"""Tests for utils/peer_registry.py — schema 1.1 (twin-aware fields,
is_twin_only scope), with backwards-compat for schema 1.0 ledgers.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))

import peer_registry  # noqa: E402


class _IsolatedRegistry:
    """Context manager that points peer_registry at a temp dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp()

    def __enter__(self):
        self._prev = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.tmp
        return self

    def __exit__(self, *exc):
        if self._prev is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self._prev
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestSchemaConstants(unittest.TestCase):
    def test_schema_1_1(self):
        self.assertEqual(peer_registry.SCHEMA, "rapp-peers/1.1")


class TestUpsertWithTwinFields(unittest.TestCase):
    def test_upsert_accepts_twin_fields(self):
        with _IsolatedRegistry():
            entry = peer_registry.upsert(
                "/tmp/fake-brainstem",
                7099,
                version="0.12.2",
                rappid_uuid="11111111-2222-3333-4444-555555555555",
                twin_name="alice",
                parent_repo="https://github.com/kody-w/wildhaven-ai-homes-twin.git",
                summoned_from="local-init",
            )
            self.assertEqual(entry["rappid_uuid"], "11111111-2222-3333-4444-555555555555")
            self.assertEqual(entry["twin_name"], "alice")
            self.assertEqual(entry["parent_repo"], "https://github.com/kody-w/wildhaven-ai-homes-twin.git")
            self.assertEqual(entry["summoned_from"], "local-init")
            self.assertIn("summoned_at", entry)

    def test_upsert_without_twin_fields_still_works(self):
        """Backwards-compat: upsert with no rappid_uuid succeeds (legacy callers)."""
        with _IsolatedRegistry():
            entry = peer_registry.upsert("/tmp/legacy", 7077, version="0.12.0")
            self.assertEqual(entry["port"], 7077)
            self.assertIsNone(entry.get("rappid_uuid"))


class TestIsTwinOnlyScope(unittest.TestCase):
    def test_path_under_dot_rapp_twins_is_twin_only(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, ".rapp", "twins", "11111111-2222-3333-4444-555555555555", ".brainstem")
        self.assertTrue(peer_registry._is_twin_only(path))
        self.assertFalse(peer_registry._is_global(path))

    def test_global_path_is_not_twin_only(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, ".brainstem", "src", "rapp_brainstem")
        self.assertFalse(peer_registry._is_twin_only(path))
        self.assertTrue(peer_registry._is_global(path))

    def test_project_path_is_neither_global_nor_twin_only(self):
        path = "/Users/example/myproj/.brainstem/src/rapp_brainstem"
        self.assertFalse(peer_registry._is_global(path))
        self.assertFalse(peer_registry._is_twin_only(path))

    def test_upsert_twin_only_marks_scope(self):
        with _IsolatedRegistry():
            home = os.path.expanduser("~")
            twin_path = os.path.join(
                home, ".rapp", "twins",
                "11111111-2222-3333-4444-555555555555", ".brainstem",
            )
            entry = peer_registry.upsert(
                twin_path, 7088,
                rappid_uuid="11111111-2222-3333-4444-555555555555",
                twin_name="bob",
            )
            self.assertTrue(entry["is_twin_only"])
            self.assertFalse(entry["is_global"])


class TestSchemaMigrationFromV1_0(unittest.TestCase):
    """A 1.0-format peers.json on disk loads cleanly through 1.1 code."""

    def test_load_v1_0_file(self):
        with _IsolatedRegistry() as reg:
            path = pathlib.Path(reg.tmp) / "rapp" / "peers.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "schema": "rapp-peers/1.0",
                "peers": [
                    {
                        "id": "abc123",
                        "brainstem_dir": "/legacy/path",
                        "port": 7060,
                        "is_global": True,
                        "project_name": "global",
                        "installed_at": "2026-01-01T00:00:00Z",
                        "version": "0.10.0",
                    }
                ],
            }, indent=2))
            data = peer_registry.load()
            self.assertEqual(len(data["peers"]), 1)
            p = data["peers"][0]
            self.assertEqual(p["port"], 7060)
            # Migrated fields default to safe values
            self.assertIsNone(p.get("rappid_uuid"))
            self.assertFalse(p.get("is_twin_only", False))


class TestGroupByTwin(unittest.TestCase):
    def test_group_by_twin_collects_parallel_incarnations(self):
        with _IsolatedRegistry():
            peer_registry.upsert(
                "/tmp/global-host", 7071,
                rappid_uuid="aaaa-1111", twin_name="alice",
            )
            peer_registry.upsert(
                "/tmp/project-host", 7072,
                rappid_uuid="aaaa-1111", twin_name="alice",
            )
            peer_registry.upsert(
                "/tmp/bob-host", 7073,
                rappid_uuid="bbbb-2222", twin_name="bob",
            )
            grouped = peer_registry.group_by_twin()
            self.assertEqual(len(grouped["aaaa-1111"]), 2)
            self.assertEqual(len(grouped["bbbb-2222"]), 1)
            self.assertEqual(grouped["aaaa-1111"][0]["twin_name"], "alice")


if __name__ == "__main__":
    unittest.main()
