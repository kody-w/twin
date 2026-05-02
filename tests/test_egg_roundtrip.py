"""Tests for utils/egg.py — pack_twin_from_repo + summon_twin_egg roundtrip.

Pure stdlib unittest. No flask, no network. Synthesizes a fake variant
repo in a temp dir, packs it, summons it into a different temp dir,
asserts content + identity preserved.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import zipfile

# Vendor the project's utils/ onto sys.path so we can import egg directly.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))

import egg  # noqa: E402


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_fake_variant_repo(root: pathlib.Path) -> dict:
    """Build a minimal hatched variant repo on disk for pack tests."""
    rappid_uuid = "11111111-2222-3333-4444-555555555555"
    parent_rappid_uuid = "37ad22f5-ed6d-48b1-b8b4-61019f58a42b"
    rj = {
        "schema": "rapp-rappid/1.1",
        "rappid": rappid_uuid,
        "parent_rappid": parent_rappid_uuid,
        "parent_repo": "https://github.com/example/parent.git",
        "parent_commit": "deadbeef",
        "born_at": "2026-05-02T00:00:00Z",
        "name": "test-twin",
        "role": "variant",
        "kind": "test-fixture",
        "description": "Synthetic twin for egg roundtrip tests.",
        "attestation": None,
        "brainstem": {
            "version": "0.12.2",
            "source_repo": "https://github.com/kody-w/RAPP.git",
            "source_commit": "0123456789abcdef",
        },
    }
    (root / "rappid.json").write_text(json.dumps(rj, indent=2))
    (root / "brainstem.py").write_text("# kernel snapshot\nprint('hello from kernel')\n")
    (root / "soul.md").write_text("# soul\nyou are the test twin.\n")
    (root / "MANIFEST.md").write_text("# manifest\n")
    (root / "README.md").write_text("# test twin\n")
    (root / "agents").mkdir()
    (root / "agents" / "basic_agent.py").write_text("# basic agent\nclass BasicAgent: pass\n")
    (root / "agents" / "custom_agent.py").write_text("# variant-specific\n")
    (root / "utils").mkdir()
    (root / "utils" / "body_functions").mkdir()
    (root / "utils" / "body_functions" / "manifest_body_function.py").write_text("# bf\n")
    (root / "utils" / "lineage_check.py").write_text("# lineage stub\n")
    (root / "installer").mkdir()
    (root / "installer" / "VERSION").write_text("0.12.2\n")
    (root / "installer" / "requirements.txt").write_text("flask>=2.0.0\n")
    (root / "installer" / "start.sh").write_text("#!/bin/bash\nexec python utils/boot.py\n")
    # synthetic .brainstem_data state
    (root / ".brainstem_data").mkdir()
    (root / ".brainstem_data" / "memory.json").write_text('{"facts": ["the twin remembered something"]}')
    (root / ".brainstem_data" / "identity.json").write_text(json.dumps({
        "twin": "rappid:twin:@kody-w/test:abcdef0123456789",
        "rapps": {},
    }))
    return rj


# ── Tests ───────────────────────────────────────────────────────────────


class TestEggSchemaConstants(unittest.TestCase):
    def test_schema_2_1_exposed(self):
        self.assertEqual(egg.EGG_SCHEMA_V2_1, "brainstem-egg/2.1")

    def test_schema_2_0_still_exposed(self):
        self.assertEqual(egg.EGG_SCHEMA_V2, "brainstem-egg/2.0")


class TestPackTwinFromRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = pathlib.Path(self.tmp) / "src"
        self.repo.mkdir()
        self.rj = _make_fake_variant_repo(self.repo)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_returns_bytes(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        self.assertIsInstance(blob, bytes)
        self.assertGreater(len(blob), 100)

    def test_is_valid_zip(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            names = z.namelist()
            self.assertIn("manifest.json", names)

    def test_manifest_has_schema_2_1(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            mf = json.loads(z.read("manifest.json"))
        self.assertEqual(mf["schema"], "brainstem-egg/2.1")
        self.assertEqual(mf["type"], "twin")

    def test_manifest_carries_source_block(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            mf = json.loads(z.read("manifest.json"))
        self.assertIn("source", mf)
        self.assertEqual(mf["source"]["rappid_uuid"], self.rj["rappid"])
        self.assertEqual(mf["source"]["parent_rappid_uuid"], self.rj["parent_rappid"])
        self.assertEqual(mf["source"]["repo"], self.rj["parent_repo"])

    def test_manifest_carries_brainstem_pin(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            mf = json.loads(z.read("manifest.json"))
        self.assertIn("brainstem", mf)
        self.assertEqual(mf["brainstem"]["version"], "0.12.2")

    def test_payload_includes_repo_tree(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            names = set(z.namelist())
        self.assertIn("repo/brainstem.py", names)
        self.assertIn("repo/soul.md", names)
        self.assertIn("repo/agents/basic_agent.py", names)
        self.assertIn("repo/agents/custom_agent.py", names)
        self.assertIn("repo/installer/VERSION", names)

    def test_payload_includes_brainstem_data(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            names = set(z.namelist())
        self.assertIn("data/memory.json", names)
        self.assertIn("data/identity.json", names)

    def test_payload_excludes_secrets_and_caches(self):
        # synthesize secrets that MUST be excluded
        (self.repo / ".env").write_text("SECRET=xyz")
        (self.repo / "__pycache__").mkdir()
        (self.repo / "__pycache__" / "junk.pyc").write_text("garbage")
        (self.repo / ".brainstem_data" / "private").mkdir()
        (self.repo / ".brainstem_data" / "private" / "leak.txt").write_text("leak")
        blob = egg.pack_twin_from_repo(str(self.repo))
        with zipfile.ZipFile(__import__("io").BytesIO(blob), "r") as z:
            names = z.namelist()
        for name in names:
            self.assertNotIn(".env", name)
            self.assertNotIn("__pycache__", name)
            self.assertNotIn("/private/", name)


class TestSummonTwinEgg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = pathlib.Path(self.tmp) / "src"
        self.repo.mkdir()
        self.rj = _make_fake_variant_repo(self.repo)
        self.host = pathlib.Path(self.tmp) / "host"
        self.host.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_summon_creates_workspace(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = egg.summon_twin_egg(blob, str(self.host))
        ws = pathlib.Path(workspace)
        self.assertTrue(ws.exists())
        self.assertTrue(ws.is_dir())

    def test_summon_workspace_under_rappid(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = egg.summon_twin_egg(blob, str(self.host))
        # workspace should include the rappid_uuid in its path
        self.assertIn(self.rj["rappid"], workspace)

    def test_summon_restores_brainstem_py(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = egg.summon_twin_egg(blob, str(self.host))
        kernel = pathlib.Path(workspace) / "brainstem.py"
        self.assertTrue(kernel.exists())
        self.assertIn("hello from kernel", kernel.read_text())

    def test_summon_restores_brainstem_data(self):
        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = egg.summon_twin_egg(blob, str(self.host))
        memory = pathlib.Path(workspace) / ".brainstem_data" / "memory.json"
        self.assertTrue(memory.exists())
        data = json.loads(memory.read_text())
        self.assertIn("the twin remembered something", data["facts"][0])

    def test_summon_preserves_identity(self):
        """The summoned workspace's rappid.json must carry the same rappid_uuid."""
        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = egg.summon_twin_egg(blob, str(self.host))
        rj_summoned = json.loads((pathlib.Path(workspace) / "rappid.json").read_text())
        self.assertEqual(rj_summoned["rappid"], self.rj["rappid"])
        self.assertEqual(rj_summoned["parent_rappid"], self.rj["parent_rappid"])

    def test_double_summon_is_idempotent(self):
        """Summoning the same egg twice into the same host should land in the same workspace, not duplicate."""
        blob = egg.pack_twin_from_repo(str(self.repo))
        ws1 = egg.summon_twin_egg(blob, str(self.host))
        ws2 = egg.summon_twin_egg(blob, str(self.host))
        self.assertEqual(ws1, ws2)


class TestRoundtripIntegrity(unittest.TestCase):
    """End-to-end: pack a repo, summon it, content matches by file hash."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = pathlib.Path(self.tmp) / "src"
        self.repo.mkdir()
        _make_fake_variant_repo(self.repo)
        self.host = pathlib.Path(self.tmp) / "host"
        self.host.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_critical_files_match(self):
        import hashlib

        blob = egg.pack_twin_from_repo(str(self.repo))
        workspace = pathlib.Path(egg.summon_twin_egg(blob, str(self.host)))
        for rel in [
            "brainstem.py",
            "soul.md",
            "agents/basic_agent.py",
            "agents/custom_agent.py",
            "utils/lineage_check.py",
            "installer/VERSION",
        ]:
            src = self.repo / rel
            dst = workspace / rel
            self.assertTrue(dst.exists(), f"missing in workspace: {rel}")
            self.assertEqual(
                hashlib.sha256(src.read_bytes()).hexdigest(),
                hashlib.sha256(dst.read_bytes()).hexdigest(),
                f"content mismatch: {rel}",
            )


if __name__ == "__main__":
    unittest.main()
