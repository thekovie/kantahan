"""Command line entry point: kantahan-catalog <command>. All output stays under --work."""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml

from . import db, runner
from .build import BuildError, build_bundle
from .discover import (
    DiscoveredLink,
    diff_links,
    load_links,
    parse_html_sections,
    parse_source_a,
    save_links,
)
from .fetch import Fetcher, FetchError
from .importer import FILE_KEY, ensure_source, import_pdf
from .publish import (
    DEFAULT_KEEP,
    PublishError,
    load_display,
    publish,
    rollback,
    set_suspended,
    withdraw_release,
)

SCRIPT_SRC = re.compile(r'src="((?:https?:)?//[^"]*songlist-update-data\.js[^"]*)"')
DEFAULT_SECTION = "REYNA SERIES"
Out = Callable[[str], None]


def _say(text: str) -> None:
    sys.stdout.write(text + "\n")


def _sources(path: Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {s["id"].lower(): s for s in data["sources"]}


def _pdf_path(work: Path, url: str) -> Path:
    match = FILE_KEY.search(url)
    key = match.group(1) if match else hashlib.sha256(url.encode()).hexdigest()[:16]
    return work / "pdfs" / f"{key}.pdf"


def cmd_migrate(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    done = db.rollback(conn, args.down) if args.down else db.migrate(conn)
    out(f"{'reverted' if args.down else 'applied'} migrations: {done or 'none'}")
    return 0


def cmd_discover(args: argparse.Namespace, out: Out, fetcher: Fetcher, **_: Any) -> int:
    sources = _sources(args.sources)
    found: list[DiscoveredLink] = []
    page_a = fetcher.get(sources["a"]["url"]).body.decode("utf-8", "replace")
    script = SCRIPT_SRC.search(page_a)
    if not script:
        raise FetchError("Source A page no longer references songlist-update-data.js")
    src = script.group(1)
    script_url = ("https:" + src) if src.startswith("//") else src
    found += parse_source_a(fetcher.get(script_url).body.decode("utf-8", "replace"))
    for sid in ("b", "c"):
        found += parse_html_sections(
            fetcher.get(sources[sid]["url"]).body.decode("utf-8", "replace"), sid
        )
    target = args.work / "discovered.json"
    previous = load_links(target) if target.exists() else []
    save_links(target, found)
    diff = diff_links(previous, found)
    out(
        f"discovered {len(found)} links; added {len(diff.added)}, removed {len(diff.removed)}, "
        f"changed {len(diff.changed)}"
    )
    for link in diff.removed:
        out(f"  REMOVED {link.source} {link.section} {link.label}")
    return 0


def _section_links(args: argparse.Namespace) -> list[DiscoveredLink]:
    links = load_links(args.work / "discovered.json")
    wanted = args.section.upper()
    return [x for x in links if x.section.upper() == wanted and x.source in args.from_sources]


def cmd_fetch(args: argparse.Namespace, out: Out, fetcher: Fetcher, **_: Any) -> int:
    fetched = skipped = failed = 0
    for link in _section_links(args):
        dest = _pdf_path(args.work, link.url)
        if dest.exists() and not args.refresh:
            skipped += 1
            continue
        try:
            fetcher.download_pdf(link.url, dest)
            fetched += 1
        except FetchError as exc:
            failed += 1
            out(f"  FAILED {link.label}: {exc}")
    out(f"fetched {fetched}, already present {skipped}, failed {failed}")
    return 1 if failed else 0


def cmd_import(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    sources = _sources(args.sources)
    for sid in args.from_sources:
        if sid not in sources:
            raise ValueError(f"unknown source {sid!r}; known: {sorted(sources)}")
        ensure_source(conn, sid, sources[sid]["url"], sources[sid]["priority"])
    tally: dict[str, int] = {}
    for link in _section_links(args):
        path = _pdf_path(args.work, link.url)
        if not path.exists():
            out(f"  MISSING {link.label}: run fetch first")
            continue
        result = import_pdf(
            conn,
            path,
            source_slug=link.source,
            url=link.url,
            label=link.label,
            retry_quarantined=args.retry_quarantined,
        )
        tally[result.outcome] = tally.get(result.outcome, 0) + 1
        if result.outcome == "quarantined":
            reasons = sorted({i.code for i in result.issues if i.severity == "error"})
            out(f"  QUARANTINED {link.label}: {reasons}")
    out("import: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    return 0


def _count(conn: sqlite3.Connection, sql: str, *params: str) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def cmd_stats(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    documents = _count(conn, "SELECT count(*) FROM document")
    open_quarantine = _count(conn, "SELECT count(*) FROM quarantine WHERE resolved_at IS NULL")
    out(f"documents: {documents} (open quarantine records {open_quarantine})")
    for status in ("mapped", "held"):
        releases = _count(conn, "SELECT count(*) FROM release WHERE status = ?", status)
        songs = _count(
            conn,
            "SELECT count(*) FROM song_entry se JOIN release r ON r.id = se.release_id "
            "WHERE r.status = ?",
            status,
        )
        out(f"releases {status}: {releases}, songs {songs}")
    out(f"canonical songs: {_count(conn, 'SELECT count(*) FROM song')}")
    return 0


def cmd_build(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    try:
        result = build_bundle(conn, args.model, args.work / "releases")
    except BuildError as exc:
        out(f"build failed: {exc}")
        return 1
    out(
        f"{result.status}: {result.songs} songs, {result.artists_withheld} artists withheld, "
        f"{result.titles_excluded} rows left out (uncertain title), "
        f"{len(result.conflicts)} conflicts -> {result.path} (sha256 {result.sha256[:12]})"
    )
    return 0 if result.status == "validated" else 2


def _publish_dir(args: argparse.Namespace) -> Path:
    return Path(args.out) if args.out else args.work / "publish"


def _do_publish(
    args: argparse.Namespace, out: Out, conn: sqlite3.Connection, allow_drop: bool
) -> str:
    result = publish(
        conn,
        _publish_dir(args),
        load_display(args.display),
        keep=args.keep,
        allow_drop=allow_drop or args.allow_drop,
    )
    for note in result.skipped:
        out(f"  skipped {note}")
    songs = ", ".join(f"{slug} {n}" for slug, n in sorted(result.songs.items()))
    out(f"{result.outcome} {result.version}: {songs}")
    return result.outcome


def cmd_publish(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    with runner.run_lock(args.work):
        _do_publish(args, out, conn, allow_drop=False)
    return 0


def cmd_rollback(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    with runner.run_lock(args.work):
        rollback(conn, _publish_dir(args), args.version)
    out(f"live catalog is now {args.version}")
    return 0


def cmd_suspend(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    suspend = args.command == "suspend"
    with runner.run_lock(args.work):
        set_suspended(
            conn, _publish_dir(args), suspend, getattr(args, "notice", None) if suspend else None
        )
    out("catalog suspended: apps will hide it" if suspend else "catalog resumed")
    return 0


def cmd_withdraw(args: argparse.Namespace, out: Out, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    with runner.run_lock(args.work):
        withdraw_release(conn, label=args.release, release_id=args.release_id)
        out("release withdrawn; publishing a catalog without it")
        try:
            _do_publish(args, out, conn, allow_drop=True)
        except PublishError as exc:
            out(f"error: {exc}")
            out("the release stays withdrawn, but the live catalog still contains it;")
            out("run `suspend` to hide the catalog until a new one can be published")
            return 1
    return 0


def _sub(args: argparse.Namespace, **extra: Any) -> argparse.Namespace:
    base = {"section": DEFAULT_SECTION, "from_sources": ["a"], "refresh": False}
    return argparse.Namespace(**{**vars(args), **base, "retry_quarantined": False, **extra})


def _run_steps(
    args: argparse.Namespace, out: Out, fetcher: Fetcher, conn: sqlite3.Connection
) -> tuple[int, str, dict[str, Any]]:
    stats: dict[str, Any] = {}
    steps: tuple[tuple[str, Callable[..., int]], ...] = (
        ("discover", cmd_discover),
        ("fetch", cmd_fetch),
        ("import", cmd_import),
    )
    for name, step in steps:
        if step(_sub(args), out, fetcher=fetcher):
            return 1, f"{name}-failed", stats
    stats["open_quarantine"] = _count(
        conn, "SELECT count(*) FROM quarantine WHERE resolved_at IS NULL"
    )
    if stats["open_quarantine"]:
        out(f"WARNING: {stats['open_quarantine']} document(s) in quarantine; they add no songs")
    return 0, _do_publish(args, out, conn, allow_drop=False), stats


def cmd_run(args: argparse.Namespace, out: Out, fetcher: Fetcher, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    kind = "manual" if args.manual else "scheduled"
    if kind == "scheduled" and not runner.is_due(conn, args.min_interval_days):
        out(f"not due: a scheduled run succeeded within {args.min_interval_days} days")
        return 0
    with runner.run_lock(args.work):
        run_id = runner.start_run(conn, kind)
        try:
            code, outcome, stats = _run_steps(args, out, fetcher, conn)
        except PublishError as exc:
            out(f"error: {exc}")
            code, outcome, stats = (
                (2 if exc.blocked else 1),
                "blocked" if exc.blocked else "error",
                {},
            )
        except BaseException:
            runner.finish_run(conn, run_id, "error", {})
            raise
        runner.finish_run(conn, run_id, outcome, stats)
    return code


def cmd_audit(args: argparse.Namespace, out: Out, fetcher: Fetcher, **_: Any) -> int:
    conn = db.connect(args.work / "catalog.sqlite")
    db.migrate(conn)
    with runner.run_lock(args.work):
        run_id = runner.start_run(conn, "audit")
        result = runner.audit_links(conn, fetcher, _section_links(_sub(args)))
        drift = bool(result.changed or result.failed)
        runner.finish_run(
            conn,
            run_id,
            "drift" if drift else "clean",
            {
                "checked": result.checked,
                "changed": list(result.changed),
                "failed": list(result.failed),
            },
        )
    for label in result.changed:
        out(f"  CHANGED {label}: the file behind this link is not the one imported")
    for label in result.failed:
        out(f"  FAILED {label}: could not be downloaded")
    out(
        f"audit: checked {result.checked}, changed {len(result.changed)}, "
        f"failed {len(result.failed)}, not yet imported {result.new}"
    )
    if result.changed:
        out("to take a changed file: fetch --refresh, import, then publish")
    return 2 if drift else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kantahan-catalog", description=__doc__)
    p.add_argument("--work", type=Path, default=Path("work"), help="output folder (gitignored)")
    p.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    p.add_argument(
        "--display", type=Path, default=Path("display.yaml"), help="model names and hues"
    )
    p.add_argument(
        "--out", type=Path, default=None, help="publish folder (default: <work>/publish)"
    )
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("migrate", help="apply (or with --down N revert) database migrations")
    m.add_argument("--down", type=int, default=0)
    sub.add_parser("discover", help="read the approved index pages and record document links")
    for name, helptext in (
        ("fetch", "download documents (polite, allowlisted)"),
        ("import", "import downloaded documents into the database"),
    ):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--section", default=DEFAULT_SECTION)
        s.add_argument("--from", dest="from_sources", nargs="+", default=["a"], type=str.lower)
        if name == "fetch":
            s.add_argument("--refresh", action="store_true", help="download even if present")
        else:
            s.add_argument(
                "--retry-quarantined",
                action="store_true",
                help="evaluate quarantined documents again (after an extractor fix)",
            )
    sub.add_parser("stats", help="show database counts")
    b = sub.add_parser("build", help="build a local catalog bundle for one model")
    b.add_argument("--model", default="reyna")
    pub = sub.add_parser("publish", help="build all models and publish a new version")
    pub.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="versions to keep on disk")
    pub.add_argument("--allow-drop", action="store_true", help="allow a big drop in songs")
    r = sub.add_parser("run", help="discover, fetch, import and publish (what cron runs)")
    r.add_argument("--manual", action="store_true", help="run now, ignoring the interval")
    r.add_argument("--min-interval-days", type=int, default=14)
    r.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    r.add_argument("--allow-drop", action="store_true")
    sub.add_parser("audit", help="re-download every document and report files that changed")
    rb = sub.add_parser("rollback", help="point the live catalog at an older version")
    rb.add_argument("version", help="for example v3")
    s = sub.add_parser("suspend", help="make apps hide the catalog (bundles stay in place)")
    s.add_argument("--notice", default=None, help="text the app shows instead of songs")
    sub.add_parser("resume", help="show the catalog again")
    w = sub.add_parser("withdraw", help="leave a release out of the catalog and publish")
    w.add_argument("--release", default=None, help="release label, for example 'Volume 64'")
    w.add_argument("--release-id", type=int, default=None)
    w.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    w.add_argument("--allow-drop", action="store_true")
    return p


COMMANDS: dict[str, Callable[..., int]] = {
    "migrate": cmd_migrate,
    "discover": cmd_discover,
    "fetch": cmd_fetch,
    "import": cmd_import,
    "stats": cmd_stats,
    "build": cmd_build,
    "publish": cmd_publish,
    "run": cmd_run,
    "audit": cmd_audit,
    "rollback": cmd_rollback,
    "suspend": cmd_suspend,
    "resume": cmd_suspend,
    "withdraw": cmd_withdraw,
}


def main(
    argv: Sequence[str] | None = None, *, fetcher: Fetcher | None = None, out: Out = _say
) -> int:
    args = parser().parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    needs_network = args.command in ("discover", "fetch", "run", "audit")
    try:
        return COMMANDS[args.command](
            args, out, fetcher=(fetcher or Fetcher()) if needs_network else None
        )
    except PublishError as exc:
        out(f"error: {exc}")
        return 2 if exc.blocked else 1
    except (FetchError, ValueError, runner.RunLocked) as exc:
        out(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
