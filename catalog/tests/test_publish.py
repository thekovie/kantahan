import hashlib
import json
import shutil

import pytest
from conftest import sample_rows

from kantahan_catalog import publish as publish_module
from kantahan_catalog.importer import import_pdf
from kantahan_catalog.publish import (
    Display,
    ModelDisplay,
    PublishError,
    load_display,
    publish,
    read_manifest,
    rollback,
    set_suspended,
    withdraw_release,
)

DISPLAY = Display(
    source_label="Test source",
    source_url="https://example.test/source",
    models={"reyna": ModelDisplay(name="Reyna", family="Reyna series", hue="magenta")},
)


def add(conn, path, n):
    return import_pdf(
        conn,
        path,
        source_slug="a",
        url=f"https://www.mediafire.com/file/k{n}/f.pdf/file",
        label=f"Volume {n}",
    )


@pytest.fixture
def loaded(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(15000, 50)), 1)
    return conn


def pub(conn, out, **kw):
    return publish(conn, out, DISPLAY, **kw)


def test_publish_writes_an_immutable_version_and_the_manifest(loaded, tmp_path):
    result = pub(loaded, tmp_path)
    assert result.outcome == "published" and result.version == "v1"
    manifest = read_manifest(tmp_path)
    assert manifest["version"] == "v1" and manifest["suspended"] is False
    assert manifest["synthetic"] is False and manifest["schema"] == 1
    model = manifest["models"][0]
    assert model["file"] == "v1/reyna.json" and model["songs"] == 50
    assert model["name"] == "Reyna" and model["hue"] == "magenta"
    assert model["coverage"] == "Volume 1"
    payload = (tmp_path / "v1" / "reyna.json").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == model["sha256"]
    assert len(payload) == model["bytes"]
    assert json.loads((tmp_path / "v1" / "manifest.json").read_text()) == manifest
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging")]


def test_publishing_unchanged_data_does_nothing(loaded, tmp_path):
    pub(loaded, tmp_path)
    again = pub(loaded, tmp_path)
    assert again.outcome == "unchanged" and again.version == "v1"
    assert not (tmp_path / "v2").exists()


def test_new_volume_makes_a_new_version_and_keeps_the_old_one(loaded, pdf, tmp_path):
    pub(loaded, tmp_path)
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)
    result = pub(loaded, tmp_path)
    assert result.version == "v2" and read_manifest(tmp_path)["models"][0]["songs"] == 100
    assert (tmp_path / "v1" / "reyna.json").exists()
    assert read_manifest(tmp_path)["models"][0]["coverage"] == "Volumes 1 to 2"


def test_conflicting_numbers_block_publishing_and_leave_the_live_manifest(loaded, pdf, tmp_path):
    pub(loaded, tmp_path)
    before = (tmp_path / "manifest.json").read_bytes()
    add(loaded, pdf("b.pdf", [("15001", "Changed title", "Other")]), 2)
    with pytest.raises(PublishError) as err:
        pub(loaded, tmp_path)
    assert err.value.blocked and "conflict" in str(err.value)
    assert (tmp_path / "manifest.json").read_bytes() == before
    assert not (tmp_path / "v2").exists()


def test_withdrawing_everything_is_an_error_not_an_empty_catalog(loaded, tmp_path):
    pub(loaded, tmp_path)
    loaded.execute("UPDATE release SET withdrawn_at = '2026-01-01'")
    loaded.execute("UPDATE release SET withdrawn_at = NULL WHERE 0")
    with pytest.raises(PublishError):
        pub(loaded, tmp_path)  # nothing left to publish is an error, not a silent empty catalog
    assert read_manifest(tmp_path)["version"] == "v1"


def test_drop_over_the_limit_is_blocked(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)
    conn.execute("UPDATE release SET withdrawn_at = '2026-01-01' WHERE label = 'Volume 2'")
    with pytest.raises(PublishError) as err:
        pub(conn, tmp_path)
    assert err.value.blocked and "dropped" in str(err.value)
    assert pub(conn, tmp_path, allow_drop=True).outcome == "published"
    assert read_manifest(tmp_path)["models"][0]["songs"] == 100


def test_old_versions_are_pruned_but_not_the_live_one(conn, pdf, tmp_path):
    for n in range(1, 5):
        add(conn, pdf(f"{n}.pdf", sample_rows(15000 + n * 1000, 50)), n)
        pub(conn, tmp_path, keep=2)
    kept = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("v"))
    assert kept == ["v3", "v4"]


def test_a_failed_publish_leaves_the_live_catalog_alone(loaded, pdf, tmp_path, monkeypatch):
    pub(loaded, tmp_path)
    before = (tmp_path / "manifest.json").read_bytes()
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("kantahan_catalog.publish._swap_manifest", boom)
    with pytest.raises(OSError):
        pub(loaded, tmp_path)
    assert (tmp_path / "manifest.json").read_bytes() == before
    assert not (tmp_path / "v2").exists()
    status = loaded.execute("SELECT status FROM publication ORDER BY id DESC").fetchone()[0]
    assert status == "failed"


def test_rollback_points_the_manifest_at_an_older_version(loaded, pdf, tmp_path):
    pub(loaded, tmp_path)
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(loaded, tmp_path)
    rollback(loaded, tmp_path, "v1")
    manifest = read_manifest(tmp_path)
    assert manifest["version"] == "v1" and manifest["models"][0]["songs"] == 50


def test_rollback_refuses_unknown_or_tampered_versions(loaded, tmp_path):
    pub(loaded, tmp_path)
    with pytest.raises(PublishError, match="no such version"):
        rollback(loaded, tmp_path, "v9")
    with pytest.raises(PublishError, match="not a version"):
        rollback(loaded, tmp_path, "../x")
    (tmp_path / "v1" / "reyna.json").write_bytes(b"{}")
    with pytest.raises(PublishError, match="hash"):
        rollback(loaded, tmp_path, "v1")


def test_suspend_and_resume_flip_the_flag_and_survive_a_publish(loaded, pdf, tmp_path):
    pub(loaded, tmp_path)
    set_suspended(loaded, tmp_path, True, notice="Paused while a request is reviewed.")
    manifest = read_manifest(tmp_path)
    assert manifest["suspended"] is True and "reviewed" in manifest["notice"]
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(loaded, tmp_path)
    assert read_manifest(tmp_path)["suspended"] is True
    set_suspended(loaded, tmp_path, False)
    after = read_manifest(tmp_path)
    assert after["suspended"] is False and "notice" not in after


def test_withdrawn_release_leaves_the_next_build(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)
    assert withdraw_release(conn, label="Volume 2") == ["reyna"]
    assert pub(conn, tmp_path, allow_drop=True).version == "v2"
    assert read_manifest(tmp_path)["models"][0]["songs"] == 100


def test_withdraw_needs_exactly_one_match(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(15000, 5)), 1)
    with pytest.raises(PublishError, match="no live release"):
        withdraw_release(conn, label="Volume 9")


def test_display_file_is_validated(tmp_path):
    path = tmp_path / "display.yaml"
    path.write_text(
        "source: {label: L, url: 'https://x.test'}\n"
        "models:\n  reyna: {name: Reyna, family: Reyna series, hue: pink}\n"
    )
    with pytest.raises(PublishError, match="hue"):
        load_display(path)
    path.write_text(
        "source: {label: L, url: 'https://x.test'}\n"
        "models:\n  reyna: {name: Reyna, family: Reyna series, hue: magenta}\n"
    )
    assert load_display(path).models["reyna"].hue == "magenta"


def test_an_existing_version_folder_is_never_deleted_by_a_failed_publish(loaded, pdf, tmp_path):
    pub(loaded, tmp_path)
    loaded.execute("DELETE FROM publication")  # as if the database came from an older backup
    loaded.execute("DELETE FROM sqlite_sequence WHERE name = 'publication'")
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)
    with pytest.raises(PublishError, match="already exists") as err:
        pub(loaded, tmp_path)
    assert err.value.blocked
    assert (tmp_path / "v1" / "reyna.json").exists()
    assert read_manifest(tmp_path)["version"] == "v1"


def test_display_only_changes_are_published(loaded, tmp_path):
    pub(loaded, tmp_path)
    renamed = Display(
        DISPLAY.source_label,
        DISPLAY.source_url,
        {"reyna": ModelDisplay(name="Reyna 2", family="Reyna series", hue="aqua")},
    )
    result = publish(loaded, tmp_path, renamed)
    assert result.outcome == "published" and result.version == "v2"
    assert read_manifest(tmp_path)["models"][0]["hue"] == "aqua"


def test_leftover_staging_folders_are_removed(loaded, tmp_path):
    (tmp_path / ".staging-999").mkdir()
    (tmp_path / ".staging-999" / "reyna.json").write_text("{}")
    pub(loaded, tmp_path)
    assert not (tmp_path / ".staging-999").exists()


def test_withdrawn_content_cannot_come_back_through_rollback(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)  # v1 holds both volumes
    withdraw_release(conn, label="Volume 2")
    pub(conn, tmp_path, allow_drop=True, keep=1)  # v2 without it; v1 is pruned
    assert not (tmp_path / "v1").exists()
    with pytest.raises(PublishError, match="no such version v1"):
        rollback(conn, tmp_path, "v1")


def test_rollback_refuses_a_restored_version_that_predates_a_withdrawal(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)
    backup = tmp_path.parent / (tmp_path.name + "-backup")
    shutil.copytree(tmp_path / "v1", backup)
    withdraw_release(conn, label="Volume 2")
    pub(conn, tmp_path, allow_drop=True)
    shutil.copytree(backup, tmp_path / "v1")  # someone puts the old folder back by hand
    with pytest.raises(PublishError, match="still contains a release that was withdrawn"):
        rollback(conn, tmp_path, "v1")


def test_version_names_must_match_exactly(loaded, tmp_path):
    pub(loaded, tmp_path)
    with pytest.raises(PublishError, match="not a version"):
        rollback(loaded, tmp_path, "v1\n")


def test_display_file_rejects_odd_shapes(tmp_path):
    path = tmp_path / "display.yaml"
    for body, message in [
        (
            "source: {label: L, url: 'http://x.test'}\nmodels:\n  reyna: {name: R, family: F, hue: aqua}\n",
            "https",
        ),
        ("source: {label: L, url: 'https://x.test'}\nmodels:\n  reyna: just text\n", "mapping"),
        (
            f"source: {{label: L, url: 'https://x.test'}}\nmodels:\n  reyna: {{name: {'x' * 90}, family: F, hue: aqua}}\n",
            "name",
        ),
    ]:
        path.write_text(body)
        with pytest.raises(PublishError, match=message):
            load_display(path)


def test_overlong_notice_is_refused(loaded, tmp_path):
    pub(loaded, tmp_path)
    with pytest.raises(PublishError, match="too long"):
        set_suspended(loaded, tmp_path, True, notice="x" * 501)


def test_withdraw_may_only_shrink_the_models_that_lost_the_release(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)
    models = withdraw_release(conn, label="Volume 2")
    assert pub(conn, tmp_path, allow_drop=frozenset(models), keep=1).outcome == "published"
    assert not (tmp_path / "v1").exists()  # the old version still held the withdrawn songs


def test_a_later_publish_removes_old_versions_that_hold_withdrawn_songs(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 100)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    pub(conn, tmp_path)
    withdraw_release(
        conn, label="Volume 2"
    )  # the follow-up publish "failed": the old folder remains
    assert (tmp_path / "v1").exists()
    add(conn, pdf("c.pdf", sample_rows(17000, 10)), 3)
    pub(conn, tmp_path, allow_drop=True)
    assert not (tmp_path / "v1").exists() and (tmp_path / "v2").exists()


def test_a_pause_set_during_a_publish_is_not_lost(loaded, pdf, tmp_path, monkeypatch):
    pub(loaded, tmp_path)
    add(loaded, pdf("b.pdf", sample_rows(16000, 50)), 2)
    real = publish_module._build_all

    def build_then_pause(*args, **kwargs):
        built = real(*args, **kwargs)
        set_suspended(loaded, tmp_path, True, notice="Paused mid-publish.")  # lands before the swap
        return built

    monkeypatch.setattr(publish_module, "_build_all", build_then_pause)
    assert pub(loaded, tmp_path).version == "v2"
    manifest = read_manifest(tmp_path)
    assert manifest["suspended"] is True and manifest["notice"] == "Paused mid-publish."
    assert json.loads((tmp_path / "v2" / "manifest.json").read_text())["suspended"] is True
