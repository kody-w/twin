"""Tests for utils/body_functions/estate_body_function.py — endpoint dispatch."""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))
sys.path.insert(0, str(_REPO_ROOT / "utils" / "body_functions"))

import peer_registry  # noqa: E402
import estate_body_function as estate  # noqa: E402


class _Iso:
    """Isolate XDG registry dir + a temp HOME for ~/.rapp/."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp()

    def __enter__(self):
        self._prev = {}
        for k in ("XDG_CONFIG_HOME", "HOME", "RAPP_HOME"):
            self._prev[k] = os.environ.get(k)
        os.environ["XDG_CONFIG_HOME"] = self.tmp
        os.environ["HOME"] = self.tmp
        os.environ["RAPP_HOME"] = os.path.join(self.tmp, ".rapp")
        return self

    def __exit__(self, *exc):
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestEndpointName(unittest.TestCase):
    def test_name_is_estate(self):
        self.assertEqual(estate.name, "estate")


class TestListTwins(unittest.TestCase):
    def test_empty_registry_returns_empty_twins(self):
        with _Iso():
            result, status = estate.handle("GET", "twins", {})
            self.assertEqual(status, 200)
            self.assertEqual(result["twins"], [])
            self.assertEqual(result["schema"], "rapp-estate-view/1.0")

    def test_twins_grouped_by_rappid(self):
        with _Iso():
            peer_registry.upsert("/tmp/host1", 7071,
                                 rappid_uuid="aaaa-1111", twin_name="alice")
            peer_registry.upsert("/tmp/host2", 7072,
                                 rappid_uuid="aaaa-1111", twin_name="alice")
            peer_registry.upsert("/tmp/host3", 7073,
                                 rappid_uuid="bbbb-2222", twin_name="bob")
            result, status = estate.handle("GET", "twins", {})
            self.assertEqual(status, 200)
            self.assertEqual(len(result["twins"]), 2)
            # Each twin entry has rappid_uuid + name + list of incarnations
            twins_by_id = {t["rappid_uuid"]: t for t in result["twins"]}
            self.assertEqual(len(twins_by_id["aaaa-1111"]["incarnations"]), 2)
            self.assertEqual(len(twins_by_id["bbbb-2222"]["incarnations"]), 1)

    def test_peers_without_rappid_are_skipped(self):
        """A legacy peer without rappid_uuid does NOT appear in the estate view."""
        with _Iso():
            peer_registry.upsert("/tmp/legacy", 7077, version="0.10.0")
            result, _ = estate.handle("GET", "twins", {})
            self.assertEqual(result["twins"], [])


class TestListEggs(unittest.TestCase):
    def test_empty_eggs_dir(self):
        with _Iso():
            result, status = estate.handle("GET", "eggs", {})
            self.assertEqual(status, 200)
            self.assertEqual(result["eggs"], [])

    def test_lists_eggs_under_rapp_home(self):
        with _Iso():
            home = os.environ["RAPP_HOME"]
            eggs_dir = pathlib.Path(home) / "eggs" / "11111111-2222-3333-4444-555555555555"
            eggs_dir.mkdir(parents=True)
            (eggs_dir / "2026-05-01T00-00-00.egg").write_bytes(b"PK\x03\x04dummy")
            (eggs_dir / "2026-05-02T00-00-00.egg").write_bytes(b"PK\x03\x04dummy2")
            result, _ = estate.handle("GET", "eggs", {})
            self.assertEqual(len(result["eggs"]), 2)
            for e in result["eggs"]:
                self.assertEqual(e["rappid_uuid"], "11111111-2222-3333-4444-555555555555")


class TestUnknownRoute(unittest.TestCase):
    def test_404_on_unknown(self):
        result, status = estate.handle("GET", "no-such-route", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
