"""gh-pages publish rebases onto a moved remote and retries the push."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from publish_data import commit, copy_payload, publish, push_with_retry


def git(cwd, *args, check=True):
    proc = subprocess.run(
        ["git", "-c", "user.name=Trenchfloor Test", "-c", "user.email=test@example.com", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc


class PublishRetry(unittest.TestCase):
    def test_rebase_keeps_publisher_feed_and_remote_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare = root / "bare.git"
            src = root / "src"
            other = root / "other"
            work = root / "work"
            git(None, "init", "--bare", "-b", "gh-pages", str(bare))
            src.mkdir()
            (src / "data").mkdir()
            (src / "index.html").write_text("<p>floor</p>\n")
            (src / "data" / "feed.json").write_text(json.dumps({"events": ["v1"]}) + "\n")
            first = publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            self.assertTrue(first["ok"])
            self.assertIsNotNone(first["published"])
            git(None, "clone", str(bare), str(other))
            (other / "NOTE").write_text("from the other side\n")
            git(other, "add", "NOTE")
            git(other, "commit", "-m", "remote moved")
            git(other, "push", "origin", "HEAD:gh-pages")
            # Commit on the stale worktree, then let the retry rebase.
            (src / "data" / "feed.json").write_text(json.dumps({"events": ["v2"]}) + "\n")
            copy_payload(src, work, feed_only=True)
            self.assertTrue(commit(work, "stale feed commit"))
            push_with_retry(work, "gh-pages")
            check = root / "check"
            git(None, "clone", str(bare), str(check))
            self.assertIn("v2", (check / "data" / "feed.json").read_text())
            self.assertIn("other side", (check / "NOTE").read_text())

    def test_second_publish_fast_forwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare = root / "bare.git"
            src = root / "src"
            other = root / "other"
            work = root / "work"
            git(None, "init", "--bare", "-b", "gh-pages", str(bare))
            src.mkdir()
            (src / "index.html").write_text("ok\n")
            (src / "data").mkdir()
            (src / "data" / "feed.json").write_text("{}\n")
            publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            git(None, "clone", str(bare), str(other))
            (other / "EXTRA").write_text("kept\n")
            git(other, "add", "EXTRA")
            git(other, "commit", "-m", "extra")
            git(other, "push", "origin", "HEAD:gh-pages")
            (src / "data" / "feed.json").write_text('{"events":[1]}\n')
            result = publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            self.assertTrue(result["published"])
            check = root / "check"
            git(None, "clone", str(bare), str(check))
            self.assertIn("events", (check / "data" / "feed.json").read_text())
            self.assertEqual((check / "EXTRA").read_text(), "kept\n")


if __name__ == "__main__":
    unittest.main()
