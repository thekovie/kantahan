import hashlib
import json

import pytest
from conftest import sample_rows

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
    assert withdraw_release(conn, label="Volume 2") == 1
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
