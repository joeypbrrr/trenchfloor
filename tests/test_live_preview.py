import json
import tempfile
import unittest
from pathlib import Path
from publish_data import copy_payload

class PreviewPublishTests(unittest.TestCase):
    def test_live_copy_and_sanitized_snapshots_leave_root_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"root";dest=Path(tmp)/"dest"
            (root/"live").mkdir(parents=True);(root/"data/cache").mkdir(parents=True)
            (root/"index.html").write_text("ROOT UNCHANGED")
            (root/"live/index.html").write_text("LIVE PREVIEW")
            (root/"live/occupancy.js").write_text("COSMETIC ONLY")
            (root/"data/feed.json").write_text('{"events":[]}')
            (root/"data/cache/live-chat-state.json").write_text(json.dumps({"messages":[{"agent":"Data Scout","text":"Real alert","time":"now","kind":"info","pid":42}],"checklist":[]}))
            copy_payload(root,dest)
            self.assertEqual((dest/"index.html").read_text(),"ROOT UNCHANGED")
            self.assertEqual((dest/"live/index.html").read_text(),"LIVE PREVIEW")
            chat=json.loads((dest/"data/live_chat.json").read_text())
            self.assertEqual(chat["messages"][0]["text"],"Real alert")
            self.assertNotIn("pid",chat["messages"][0])
            files=copy_payload(root,dest,feed_only=True)
            self.assertIn("data/live_chat.json",files)
            self.assertIn("data/checklist.json",files)
            self.assertEqual(json.loads((dest/"data/checklist.json").read_text())["items"],[])
