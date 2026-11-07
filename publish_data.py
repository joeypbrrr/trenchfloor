#!/usr/bin/env python3
"""Publish the static site and JSON to the gh-pages branch.

Uses the machine's existing git credentials. Tokens are never accepted as
arguments. A rejected push is rebased, preferring this publisher's files,
and retried.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = "https://joeypbrrr.github.io/trenchfloor/floor/"
SITE_FILES = [
    "index.html",
    "app.js",
    "scene.js",
    "style.css",
    "three.min.js",
    "config.js",
    "manifest.webmanifest",
    "sw.js",
    ".nojekyll",
    "BEST_STRATEGY.md",
    "LESSONS.md",
    "icons/icon-192.png",
    "icons/icon-512.png",
    "data/research.json",
    "data/feed.json",
    "data/lessons.json",
    "data/ledger/index.json",
]
TOKEN_RE = re.compile(r"(https?://)([^/\s@]+)@")


def redact(text):
    return TOKEN_RE.sub(r"\1", text or "")


def git(cwd, *args, timeout=120, check=False):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(redact((proc.stderr or proc.stdout or "git failed").strip()))
    return proc


def commit(cwd, message):
    git(cwd, "add", "-A")
    quiet = git(cwd, "diff", "--cached", "--quiet")
    if quiet.returncode == 0:
        return False
    proc = git(
        cwd,
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "commit", "-m", message,
    )
    if proc.returncode != 0:
        raise RuntimeError(redact(proc.stderr or proc.stdout or "commit failed"))
    return True


def remote_has_branch(remote, branch):
    proc = git(None, "ls-remote", "--heads", remote, f"refs/heads/{branch}", timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("cannot read remote: " + redact(proc.stderr or proc.stdout))
    return bool(proc.stdout.strip())


def ensure_worktree(work, remote, branch):
    if (work / ".git").exists():
        return "existing"
    if work.exists() and any(work.iterdir()):
        raise RuntimeError(f"{work} exists and is not a git checkout")
    if remote_has_branch(remote, branch):
        work.parent.mkdir(parents=True, exist_ok=True)
        proc = git(None, "clone", "--branch", branch, "--single-branch", remote, str(work), timeout=180)
        if proc.returncode != 0:
            raise RuntimeError("clone failed: " + redact(proc.stderr or proc.stdout))
        return "cloned"
    work.mkdir(parents=True, exist_ok=True)
    proc = git(None, "init", "-b", branch, str(work))
    if proc.returncode != 0:
        raise RuntimeError(redact(proc.stderr or proc.stdout))
    git(work, "remote", "add", "origin", remote, check=True)
    return "created"


def sync(work, branch):
    """Fast-forward local gh-pages onto origin before we copy new files."""
    proc = git(work, "rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode != 0:
        return
    fetched = git(work, "fetch", "origin", branch, timeout=120)
    if fetched.returncode != 0:
        # A brand-new branch has nothing to fetch yet.
        if "couldn't find remote ref" in (fetched.stderr or "").lower() or "not found" in (fetched.stderr or "").lower():
            return
        raise RuntimeError("fetch failed: " + redact(fetched.stderr or fetched.stdout))
    head = git(work, "rev-parse", "--verify", f"origin/{branch}")
    if head.returncode != 0:
        return
    dirty = git(work, "status", "--porcelain")
    if dirty.stdout.strip():
        raise RuntimeError("publish worktree is dirty before sync; refusing to rebase over local edits")
    rebased = git(work, "-c", "user.name=joeypbrrr", "-c", "user.email=joeypbrrr@users.noreply.github.com", "rebase", f"origin/{branch}")
    if rebased.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("sync rebase failed: " + redact(rebased.stderr or rebased.stdout))


def rebase_ours(work, branch):
    """Replay our commit onto origin, keeping the publisher's file contents."""
    fetched = git(work, "fetch", "origin", branch, timeout=120)
    if fetched.returncode != 0:
        raise RuntimeError("fetch during retry failed: " + redact(fetched.stderr or fetched.stdout))
    rebased = git(work, "-c", "user.name=joeypbrrr", "-c", "user.email=joeypbrrr@users.noreply.github.com", "rebase", "-X", "theirs", f"origin/{branch}")
    if rebased.returncode == 0:
        return
    # `theirs` during a rebase is the commit being replayed: our new data.
    checkout = git(work, "checkout", "--theirs", "--", ".")
    if checkout.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("rebase conflict could not be resolved: " + redact(rebased.stderr or checkout.stderr))
    git(work, "add", "-A")
    continued = git(
        work,
        "-c", "core.editor=true",
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "rebase", "--continue",
    )
    if continued.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("rebase --continue failed: " + redact(continued.stderr or continued.stdout))


def push_with_retry(work, branch, retries=4):
    last = ""
    for _attempt in range(retries):
        proc = git(work, "push", "origin", f"HEAD:{branch}", timeout=180)
        if proc.returncode == 0:
            return
        last = redact(proc.stderr or proc.stdout)
        lowered = last.lower()
        if any(word in lowered for word in ("authentication", "permission", "403", "could not read")):
            raise RuntimeError(last)
        rebase_ours(work, branch)
    raise RuntimeError("push failed after rebase retries: " + last)


def copy_payload(root, dest, feed_only=False):
    if feed_only:
        src = root / "data" / "feed.json"
        if not src.exists():
            raise RuntimeError("data/feed.json is missing")
        target = dest / "data" / "feed.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        return ["data/feed.json"]
    copied = []
    for rel in SITE_FILES:
        src = root / rel
        if not src.exists():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
    ledger = root / "data" / "ledger"
    if ledger.exists():
        for src in ledger.glob("*.json"):
            target = dest / "data" / "ledger" / src.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied.append(f"data/ledger/{src.name}")
    research = dest / "data" / "research.json"
    if research.exists():
        try:
            raw = json.loads(research.read_text())
        except json.JSONDecodeError:
            raw = None
        if isinstance(raw, dict):
            health = raw.setdefault("health", {})
            health["public_url"] = PUBLIC
            health["last_published"] = datetime.now(timezone.utc).isoformat()
            research.write_text(json.dumps(raw, indent=2) + "\n")
    return copied


def publish(root=None, feed_only=False, remote=None, branch="gh-pages", work=None, dry_run=False):
    root = Path(root or ROOT)
    remote = remote or git(root, "remote", "get-url", "origin", check=True).stdout.strip()
    work = Path(work or (root / ".gh-pages"))
    if dry_run:
        files = [rel for rel in SITE_FILES if (root / rel).exists()]
        files += [f"data/ledger/{p.name}" for p in (root / "data" / "ledger").glob("*.json")] if (root / "data" / "ledger").exists() else []
        print("dry-run", "feed" if feed_only else "full", len(files), "files")
        return {"ok": True, "dry_run": True, "files": files}
    ensure_worktree(work, remote, branch)
    if (work / ".git").exists() and git(work, "rev-parse", "--verify", "HEAD").returncode == 0:
        sync(work, branch)
    copied = copy_payload(root, work / "floor", feed_only=feed_only)
    stamp = datetime.now(timezone.utc).isoformat()
    message = ("Feed update " if feed_only else "Research publish ") + stamp
    if not commit(work, message):
        print("no new data")
        return {"ok": True, "published": None, "detail": "no new data", "files": copied}
    push_with_retry(work, branch)
    print("published", "feed" if feed_only else "site", stamp, flush=True)
    return {"ok": True, "published": stamp, "mode": "feed" if feed_only else "full", "files": copied}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish Trenchfloor to gh-pages")
    parser.add_argument("--feed-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--branch", default="gh-pages")
    args = parser.parse_args(argv)
    try:
        result = publish(feed_only=args.feed_only, branch=args.branch, dry_run=args.dry_run)
    except Exception as exc:
        print("publish failed:", redact(str(exc))[:500], file=sys.stderr, flush=True)
        return 1
    if not result.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
