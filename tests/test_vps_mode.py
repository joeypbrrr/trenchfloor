import os
import unittest
from unittest.mock import patch
import publish_data

class ServerModeTests(unittest.TestCase):
    def test_vps_publisher_never_touches_git(self):
        with patch.dict(os.environ,{"TRENCHFLOOR_SERVER_MODE":"vps"}), patch.object(publish_data,"git",side_effect=AssertionError("Git called")):
            result=publish_data.publish(root="/nonexistent",remote="invalid")
        self.assertTrue(result["ok"])
        self.assertTrue(result["disabled"])
        self.assertIsNone(result["published"])
    def test_skip_publish_also_noops(self):
        with patch.dict(os.environ,{"TRENCHFLOOR_SKIP_PUBLISH":"1"}), patch.object(publish_data,"git",side_effect=AssertionError("Git called")):
            self.assertTrue(publish_data.publish()["disabled"])
