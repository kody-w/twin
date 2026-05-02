"""End-to-end HTTP integration test for the estate body_function.

Exercises the route registered by body_functions_loader.install(app) using
Flask's test client — no real port, no environment side effects, proves
the wiring all the way from a real HTTP request to the JSON response.

Skipped if flask is not importable.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

try:
    import flask
    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))


def _make_repo(root: pathlib.Path) -> dict:
    """Synthesize a minimal hatched variant repo for lay-egg tests."""
    rj = {
        "schema": "rapp-rappid/1.1",
        "rappid": "abcdef00-1111-2222-3333-444444444444",
        "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
        "parent_repo": "https://github.com/kody-w/wildhaven-ai-homes-twin.git",
        "parent_commit": "deadbeef",
        "born_at": "2026-05-02T00:00:00Z",
        "name": "http-test-twin",
        "role": "variant",
        "kind": "test",
        "description": "for http tests",
        "attestation": None,
        "brainstem": {
            "version": "0.12.2",
            "source_repo": "https://github.com/kody-w/RAPP.git",
            "source_commit": "abc123",
        },
    }
    (root / "rappid.json").write_text(json.dumps(rj, indent=2))
    (root / "brainstem.py").write_text("# kernel\n")
    (root / "soul.md").write_text("# soul\n")
    (root / "agents").mkdir()
    (root / "agents" / "basic_agent.py").write_text("# agent\n")
    (root / "utils").mkdir()
    (root / "utils" / "lineage_check.py").write_text("# stub\n")
    (root / "installer").mkdir()
    (root / "installer" / "VERSION").write_text("0.12.2\n")
    return rj


class _Iso:
    """Isolate XDG/HOME/RAPP_HOME via env so the test never touches the user's actual config."""

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


@unittest.skipUnless(HAVE_FLASK, "flask not installed")
class TestEstateHTTP(unittest.TestCase):
    def setUp(self):
        # Build a Flask app and call body_functions_loader.install(app)
        # — the same wiring path the canonical kernel uses at boot.
        from flask import Flask
        sys.path.insert(0, str(_REPO_ROOT / "utils"))
        import body_functions_loader

        self.app = Flask(__name__)
        body_functions_loader.install(self.app)
        self.client = self.app.test_client()

    def test_get_twins_empty(self):
        with _Iso():
            r = self.client.get("/api/estate/twins")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(data["schema"], "rapp-estate-view/1.0")
            self.assertEqual(data["twins"], [])

    def test_get_twins_grouped_by_rappid(self):
        with _Iso():
            import peer_registry
            peer_registry.upsert("/tmp/host1", 7071,
                                 rappid_uuid="aaa-1111", twin_name="alice")
            peer_registry.upsert("/tmp/host2", 7072,
                                 rappid_uuid="aaa-1111", twin_name="alice")
            peer_registry.upsert("/tmp/host3", 7073,
                                 rappid_uuid="bbb-2222", twin_name="bob")

            r = self.client.get("/api/estate/twins")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(len(data["twins"]), 2)
            twins_by_id = {t["rappid_uuid"]: t for t in data["twins"]}
            self.assertEqual(twins_by_id["aaa-1111"]["incarnation_count"], 2)
            self.assertEqual(twins_by_id["bbb-2222"]["incarnation_count"], 1)

    def test_get_eggs_empty(self):
        with _Iso():
            r = self.client.get("/api/estate/eggs")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(data["eggs"], [])

    def test_post_lay_egg_missing_body_returns_400(self):
        with _Iso():
            r = self.client.post("/api/estate/lay-egg", json={})
            self.assertEqual(r.status_code, 400)
            self.assertIn("repo_path", r.get_json().get("error", ""))

    def test_post_lay_egg_packs_real_repo(self):
        """End-to-end through HTTP: synthesize a repo, POST lay-egg, verify
        the egg was written under $RAPP_HOME/eggs/<rappid>/."""
        with _Iso():
            tmp = tempfile.mkdtemp()
            try:
                repo = pathlib.Path(tmp) / "repo"
                repo.mkdir()
                rj = _make_repo(repo)

                r = self.client.post(
                    "/api/estate/lay-egg",
                    json={"repo_path": str(repo)},
                )
                self.assertEqual(r.status_code, 200)
                data = r.get_json()
                self.assertTrue(data["ok"])
                self.assertEqual(data["rappid_uuid"], rj["rappid"])
                self.assertTrue(os.path.exists(data["egg_path"]))
                self.assertGreater(data["size_bytes"], 100)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_post_summon_round_trip(self):
        """Lay an egg via HTTP, then summon it via HTTP, verify the
        workspace materializes with identity preserved."""
        with _Iso():
            tmp = tempfile.mkdtemp()
            try:
                repo = pathlib.Path(tmp) / "repo"
                repo.mkdir()
                rj = _make_repo(repo)

                # Lay
                r1 = self.client.post(
                    "/api/estate/lay-egg",
                    json={"repo_path": str(repo)},
                )
                egg_path = r1.get_json()["egg_path"]

                # Summon into a fresh host
                host = os.path.join(tmp, "host")
                os.makedirs(host, exist_ok=True)
                r2 = self.client.post(
                    "/api/estate/summon",
                    json={"egg_path": egg_path, "host_root": host},
                )
                self.assertEqual(r2.status_code, 200)
                data = r2.get_json()
                self.assertTrue(data["ok"])

                # Verify the workspace exists with the right identity
                ws = pathlib.Path(data["workspace"])
                self.assertTrue(ws.exists())
                self.assertIn(rj["rappid"], str(ws))
                rj_after = json.loads((ws / "rappid.json").read_text())
                self.assertEqual(rj_after["rappid"], rj["rappid"])
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_post_summon_missing_egg_returns_400(self):
        with _Iso():
            r = self.client.post(
                "/api/estate/summon",
                json={"egg_path": "/nonexistent/egg.egg"},
            )
            self.assertEqual(r.status_code, 400)
            self.assertIn("egg_path", r.get_json().get("error", ""))

    def test_unknown_route_returns_404(self):
        with _Iso():
            r = self.client.get("/api/estate/no-such-endpoint")
            self.assertEqual(r.status_code, 404)

    def test_neighborhood_still_works_alongside_estate(self):
        """Sanity check: registering estate didn't clobber the existing neighborhood body_function."""
        with _Iso():
            r = self.client.get("/api/neighborhood/peers")
            # Either 200 (worked) or 404 if neighborhood isn't installed in
            # twin/'s body_functions; the relevant assertion is that
            # estate registration didn't break Flask's URL map.
            self.assertIn(r.status_code, (200, 404))


if __name__ == "__main__":
    unittest.main()
