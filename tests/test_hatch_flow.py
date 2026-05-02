"""End-to-end test for the egg-based hatching cycle.

The flow:
  1. Pack a "before" twin → egg
  2. Simulate a kernel upgrade by overwriting brainstem.py with a "newer" version
  3. Wipe local mutations (simulate a clean kernel checkout)
  4. Summon the egg back → verify the kernel STAYS at the new version while
     the twin's identity, mutations, and state are restored on top.

This is the heart of the user's insight: "we can use this for taking
updates from the kernel and then just using the locally backedup egg".
"""

import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))

import egg  # noqa: E402


def _make_full_repo(root: pathlib.Path, kernel_text: str) -> dict:
    rappid_uuid = "fade1234-5678-90ab-cdef-1234567890ab"
    rj = {
        "schema": "rapp-rappid/1.1",
        "rappid": rappid_uuid,
        "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
        "parent_repo": "https://github.com/kody-w/wildhaven-ai-homes-twin.git",
        "parent_commit": "abc123",
        "born_at": "2026-05-02T00:00:00Z",
        "name": "hatch-test-twin",
        "role": "variant",
        "kind": "test",
        "description": "twin for hatch tests",
        "attestation": None,
        "brainstem": {
            "version": "0.12.2",
            "source_repo": "https://github.com/kody-w/RAPP.git",
            "source_commit": "old-kernel-sha",
        },
    }
    (root / "rappid.json").write_text(json.dumps(rj, indent=2))
    (root / "brainstem.py").write_text(kernel_text)
    (root / "soul.md").write_text("# soul\nthe twin's voice — locally edited.\n")
    (root / "agents").mkdir()
    (root / "agents" / "basic_agent.py").write_text("# basic\n")
    (root / "agents" / "my_local_agent.py").write_text("# local mutation\n")
    (root / "utils").mkdir()
    (root / "utils" / "lineage_check.py").write_text("# stub\n")
    (root / "utils" / "body_functions").mkdir()
    (root / "installer").mkdir()
    (root / "installer" / "VERSION").write_text("0.12.2\n")
    # Memory state — the bit you cannot afford to lose during a kernel update
    (root / ".brainstem_data").mkdir()
    (root / ".brainstem_data" / "memory.json").write_text(
        json.dumps({"facts": ["important memory that must survive the hatch"]})
    )
    (root / ".brainstem_data" / "identity.json").write_text(json.dumps({
        "twin": "rappid:twin:@kody-w/hatch-test:abc123def4567890",
        "rapps": {},
    }))
    return rj


class TestHatchCycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.before = pathlib.Path(self.tmp) / "before"
        self.before.mkdir()
        self.host = pathlib.Path(self.tmp) / "host"
        self.host.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_egg_preserves_identity_across_kernel_swap(self):
        # Step 1: build the original twin and pack it
        old_kernel_text = "# kernel v0.12.2\nVERSION = '0.12.2'\nprint('old kernel')"
        original_rj = _make_full_repo(self.before, old_kernel_text)
        rappid_uuid = original_rj["rappid"]
        memory_hash = hashlib.sha256(
            (self.before / ".brainstem_data" / "memory.json").read_bytes()
        ).hexdigest()
        egg_blob = egg.pack_twin_from_repo(str(self.before))

        # Step 2: simulate kernel upgrade by writing a NEW kernel file
        # into the host workspace BEFORE summoning. This is the "fresh
        # kernel" the egg lands on.
        workspace = pathlib.Path(self.host) / rappid_uuid
        workspace.mkdir()
        new_kernel_text = "# kernel v0.13.0 (UPGRADED)\nVERSION = '0.13.0'\nprint('new kernel')"
        (workspace / "brainstem.py").write_text(new_kernel_text)

        # Step 3: summon the egg into the host (which already has the new kernel)
        # The egg should restore identity + state + non-kernel files BUT the
        # caller can opt to keep the new kernel. We test "keep_kernel=True".
        ws_path = egg.summon_twin_egg(
            egg_blob,
            str(self.host),
            keep_existing_kernel=True,
        )
        ws = pathlib.Path(ws_path)

        # Step 4: assertions
        # 4a. identity is restored from egg
        rj_after = json.loads((ws / "rappid.json").read_text())
        self.assertEqual(rj_after["rappid"], rappid_uuid)
        self.assertEqual(rj_after["name"], original_rj["name"])

        # 4b. memory survived
        memory_after_hash = hashlib.sha256(
            (ws / ".brainstem_data" / "memory.json").read_bytes()
        ).hexdigest()
        self.assertEqual(memory_after_hash, memory_hash)

        # 4c. local mutations (custom agent, soul.md) restored
        self.assertTrue((ws / "agents" / "my_local_agent.py").exists())
        self.assertIn("locally edited", (ws / "soul.md").read_text())

        # 4d. KERNEL stayed at the upgraded version (the whole point)
        kernel_text_after = (ws / "brainstem.py").read_text()
        self.assertIn("v0.13.0", kernel_text_after)
        self.assertNotIn("v0.12.2", kernel_text_after)

    def test_default_summon_replaces_kernel_with_egg_kernel(self):
        """Without keep_existing_kernel=True, the kernel from the egg replaces."""
        old_kernel_text = "# kernel v0.12.2\nprint('old')"
        _make_full_repo(self.before, old_kernel_text)
        egg_blob = egg.pack_twin_from_repo(str(self.before))

        ws_path = egg.summon_twin_egg(egg_blob, str(self.host))
        ws = pathlib.Path(ws_path)
        self.assertIn("v0.12.2", (ws / "brainstem.py").read_text())


if __name__ == "__main__":
    unittest.main()
