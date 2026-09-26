"""Offline pulse regression tests using synthetic, unsigned temporary chains."""

import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import pulse_lib as pl  # noqa: E402
import pulse_sign  # noqa: E402
import pulse_verify  # noqa: E402


def address(domain, value):
    # The fixtures have ASCII keys; this oracle does not call the pulse hasher.
    canonical = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256((domain + "\n" + canonical).encode("utf-8")).hexdigest()


def wave(frame):
    return address("rapp/1:wave", {
        key: value for key, value in frame.items()
        if key not in ("frame_hash", "sig")
    })


def current_frame(seq=0, previous=None, ops=None):
    frame = {
        "spec": "rapp/1",
        "kind": "twin.pulse",
        "stream_id": pl.TWIN_ID,
        "seq": seq,
        "utc": (datetime.datetime(2026, 1, 1) +
                datetime.timedelta(seconds=seq)).isoformat(
                    timespec="milliseconds") + "Z",
        "payload": {"bones": ops if ops is not None else {}},
        "prev": previous["payload_hash"] if previous else None,
        "prev_wave": None,
        "sig": None,
    }
    frame["payload_hash"] = address("rapp/1:particle", frame["payload"])
    frame["frame_hash"] = wave(frame)
    return frame


def current_feed(frames):
    return {
        "spec": "rapp/1",
        "kind": "twin.pulse.feed",
        "twin_id": pl.TWIN_ID,
        "stream_id": pl.TWIN_ID,
        "head_hash": frames[-1]["frame_hash"] if frames else None,
        "count": min(len(frames), pl.N),
        "frames": frames[-pl.N:],
    }


def legacy_frame():
    return {
        "spec": "rapp-frame/2.0",
        "kind": "twin.pulse",
        "seq": 0,
        "ts": "2026-01-01T00:00:00Z",
        "twin_id": pl.TWIN_ID,
        "kernel_version": "0.6.0",
        "payload": {"bones": {}},
        "sha256": hashlib.sha256(b'{"bones":{}}').hexdigest(),
        "parent_sha": None,
        "sig": None,
    }


class TestPulsePrimitives(unittest.TestCase):
    def test_builder_uses_exact_current_envelope_and_hash_domains(self):
        ops = {"note.txt": {"op": "set", "value": "synthetic bones"}}
        expected = current_frame(ops=ops)
        actual = pl.build_frame(0, ops, None, expected["utc"])
        self.assertEqual(actual, expected)

    def test_jcs_golden_vector_is_unchanged(self):
        fixtures = REPO / "scripts" / "testdata"
        value = json.loads((fixtures / "jcs_golden_input.json").read_text())
        self.assertEqual(pl.canonicalize(value),
                         (fixtures / "jcs_golden_expected.jcs").read_bytes())
        with self.assertRaises(ValueError):
            pl.canonicalize({"unsupported": 1.5})

    def test_feed_and_atom_use_wave_addresses_not_particle_addresses(self):
        first = current_frame()
        second = current_frame(1, first)
        self.assertEqual(first["payload_hash"], second["payload_hash"])
        self.assertNotEqual(first["frame_hash"], second["frame_hash"])
        feed = pl.build_feed([second, first])
        self.assertEqual(feed, current_feed([first, second]))
        atom = ET.fromstring(pl.build_feed_xml(feed))
        ns = {"a": "http://www.w3.org/2005/Atom"}
        self.assertEqual(
            [entry.find("a:id", ns).text for entry in atom.findall("a:entry", ns)],
            [first["frame_hash"], second["frame_hash"]])
        self.assertEqual(atom.find("a:updated", ns).text, second["utc"])

    def test_builders_refuse_legacy_instead_of_mixing_schemas(self):
        with self.assertRaisesRegex(ValueError, "legacy.*rapp-frame/2.0"):
            pl.build_feed([legacy_frame()])
        with self.assertRaisesRegex(ValueError, "legacy.*rapp-frame/2.0"):
            pl.replay([legacy_frame()])
        with self.assertRaisesRegex(ValueError, "legacy.*rapp-frame/2.0"):
            pl.attach_sig(legacy_frame(), b"not a private key")

    def test_current_signatures_are_not_legacy_ed25519_objects(self):
        frame = current_frame()
        self.assertTrue(pl.verify_frame_sig(frame, None))
        with self.assertRaisesRegex(ValueError, "JWS"):
            pl.attach_sig(frame, b"not a private key")
        for sig in ({"alg": "ed25519", "sig": "00" * 64}, "e30..AA"):
            with self.subTest(sig=sig):
                frame["sig"] = sig
                with self.assertRaisesRegex(ValueError, "JWS"):
                    pl.verify_frame_sig(frame, None)

    def test_current_bones_replay_preserves_set_delete_and_merge(self):
        first = current_frame(ops={
            "note.txt": {"op": "set", "value": "before"},
            "card.json": {"op": "set", "value": {"keep": 1, "remove": 2}},
        })
        second = current_frame(1, first, {
            "note.txt": {"op": "delete"},
            "card.json": {"op": "merge", "value": {"remove": None, "add": 3}},
        })
        self.assertEqual(pl.replay([first, second]),
                         {"card.json": {"keep": 1, "add": 3}})
        self.assertEqual(pl.diff_ops(
            {"card.json": {}, "old.txt": "gone"},
            {"card.json": {"keep": 1}}), {
                "card.json": {"op": "set", "value": {"keep": 1}},
                "old.txt": {"op": "delete"},
            })


class TestPulseCommands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pulse-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "frames").mkdir()
        (self.repo / "bones").mkdir()
        self.frames = [current_frame(ops={
            "note.txt": {"op": "set", "value": "before"},
        })]
        self.frames.append(current_frame(1, self.frames[0]))
        (self.repo / "bones" / "note.txt").write_text("before", encoding="utf-8")
        self.save_chain()

    def dump(self, path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def save_chain(self):
        for frame in self.frames:
            self.dump(self.repo / "frames" / ("%d.json" % frame["seq"]), frame)
        self.dump(self.repo / "feed.json", current_feed(self.frames))

    def snapshot(self):
        return {str(path.relative_to(self.repo)): path.read_bytes()
                for path in self.repo.rglob("*") if path.is_file()}

    def run_main(self, main, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["--repo", str(self.repo), *args])
        return result, stdout.getvalue() + stderr.getvalue()

    def verify(self):
        return self.run_main(pulse_verify.main, "--quiet")

    def sign(self, *args):
        return self.run_main(
            pulse_sign.main, "--no-sign", "--ts", "2026-01-01T00:00:02Z", *args)

    def assert_refused_without_writes(self, diagnostic):
        before = self.snapshot()
        result, output = self.verify()
        self.assertNotEqual(result, 0, output)
        self.assertIn(diagnostic, output)
        result, output = self.sign("--allow-empty")
        self.assertNotEqual(result, 0, output)
        self.assertIn(diagnostic, output)
        self.assertEqual(self.snapshot(), before)

    def test_verifier_accepts_current_unsigned_chain_without_keys(self):
        before = self.snapshot()
        result, output = self.verify()
        self.assertEqual(result, 0, output)
        self.assertIn("PULSE VERIFY: OK", output)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.repo / "keys").exists())

    def test_signer_appends_using_predecessor_particle_and_refreshes_feeds(self):
        before = {path: data for path, data in self.snapshot().items()
                  if path.startswith("frames/")}
        (self.repo / "bones" / "note.txt").write_text("after", encoding="utf-8")
        result, output = self.sign()
        self.assertEqual(result, 0, output)
        frame = json.loads((self.repo / "frames" / "2.json").read_text())
        expected = current_frame(2, self.frames[-1], {
            "note.txt": {"op": "set", "value": "after"},
        })
        self.assertEqual(frame, expected)
        self.assertEqual(frame["prev"], self.frames[-1]["payload_hash"])
        self.assertNotEqual(frame["prev"], self.frames[-1]["frame_hash"])
        feed = json.loads((self.repo / "feed.json").read_text())
        self.assertEqual(feed, current_feed(self.frames + [frame]))
        self.assertNotIn("head_sha", feed)
        self.assertNotIn("sha256", frame)
        self.assertFalse((self.repo / "keys").exists())
        for path, data in before.items():
            self.assertEqual((self.repo / path).read_bytes(), data)
        result, output = self.verify()
        self.assertEqual(result, 0, output)

    def test_signer_starts_current_genesis_in_empty_repo(self):
        for path in (self.repo / "frames").iterdir():
            path.unlink()
        (self.repo / "feed.json").unlink()
        result, output = self.sign()
        self.assertEqual(result, 0, output)
        frame = json.loads((self.repo / "frames" / "0.json").read_text())
        self.assertEqual(frame["spec"], "rapp/1")
        self.assertIsNone(frame["prev"])
        result, output = self.verify()
        self.assertEqual(result, 0, output)

    def test_no_change_does_not_write_but_heartbeat_extends_chain(self):
        before = self.snapshot()
        result, output = self.sign()
        self.assertEqual(result, 0, output)
        self.assertIn("no bones changes", output)
        self.assertEqual(self.snapshot(), before)
        result, output = self.sign("--allow-empty")
        self.assertEqual(result, 0, output)
        frame = json.loads((self.repo / "frames" / "2.json").read_text())
        self.assertEqual(frame, current_frame(2, self.frames[-1]))
        result, output = self.verify()
        self.assertEqual(result, 0, output)

    def test_corrupt_history_is_refused_even_when_bones_have_not_changed(self):
        self.frames[0]["payload_hash"] = "0" * 64
        self.save_chain()
        before = self.snapshot()
        result, output = self.sign()
        self.assertNotEqual(result, 0, output)
        self.assertIn("payload_hash", output)
        self.assertEqual(self.snapshot(), before)

    def test_tampering_and_broken_current_chain_are_refused(self):
        original = copy.deepcopy(self.frames)
        cases = [
            ("payload_hash", lambda f: f["payload"]["bones"].update({
                "extra.txt": {"op": "set", "value": "tampered"},
            })),
            ("frame_hash", lambda f: f.update(utc="2026-01-02T00:00:00.000Z")),
            ("prev", lambda f: f.update(prev=original[0]["frame_hash"])),
            ("prev_wave", lambda f: f.update(prev_wave=original[0]["frame_hash"])),
            ("stream_id", lambda f: f.update(stream_id="rappid:@other/twin:" + "a" * 64)),
            ("seq", lambda f: f.update(seq=True)),
            ("utc", lambda f: f.update(utc="2026-02-30T00:00:00.000Z")),
            ("utc", lambda f: f.update(utc="2026-01-01T00:00:01Z")),
            ("utc", lambda f: f.update(utc="2025-12-31T00:00:00.000Z")),
            ("eleven", lambda f: f.update(sha256="0" * 64)),
        ]
        for diagnostic, mutate in cases:
            with self.subTest(diagnostic=diagnostic, mutate=mutate):
                self.frames = copy.deepcopy(original)
                mutate(self.frames[1])
                if diagnostic not in ("payload_hash", "frame_hash"):
                    self.frames[1]["frame_hash"] = wave(self.frames[1])
                self.dump(self.repo / "frames" / "1.json", self.frames[1])
                self.dump(self.repo / "feed.json", current_feed(self.frames))
                self.assert_refused_without_writes(diagnostic)

    def test_missing_required_null_field_is_not_treated_as_present(self):
        del self.frames[0]["prev"]
        self.frames[0]["frame_hash"] = wave(self.frames[0])
        self.save_chain()
        self.assert_refused_without_writes("eleven")

    def test_legacy_and_unknown_specs_are_explicitly_refused(self):
        for spec, diagnostic in [
                ("rapp-frame/2.0", "legacy"),
                ("rapp-frame/2.1", "legacy"),
                ("rapp/99", "unsupported"),
                (None, "unsupported")]:
            with self.subTest(spec=spec):
                frame = legacy_frame()
                frame["spec"] = spec
                self.dump(self.repo / "frames" / "0.json", frame)
                self.assert_refused_without_writes(diagnostic)

    def test_explicit_archives_are_not_loaded_or_rewritten(self):
        for name in ("legacy", "attic"):
            archive = self.repo / "frames" / name
            archive.mkdir()
            (archive / "0.json").write_text("not active JSON", encoding="utf-8")
        before = self.snapshot()
        result, output = self.verify()
        self.assertEqual(result, 0, output)
        result, output = self.sign("--allow-empty")
        self.assertEqual(result, 0, output)
        for name in ("legacy", "attic"):
            path = "frames/%s/0.json" % name
            self.assertEqual((self.repo / path).read_bytes(), before[path])

    def test_unarchived_cartridge_input_is_not_silently_ignored(self):
        self.dump(self.repo / "frames" / "0-12345678.json",
                  {"sha": "0" * 64, "prevSha": None, "kind": "seed"})
        self.assert_refused_without_writes("legacy")

    def test_filename_must_match_sequence(self):
        (self.repo / "frames" / "1.json").rename(self.repo / "frames" / "7.json")
        self.assert_refused_without_writes("7.json")

    def test_sequence_gaps_are_refused(self):
        (self.repo / "frames" / "1.json").unlink()
        self.frames[1]["seq"] = 2
        self.frames[1]["frame_hash"] = wave(self.frames[1])
        self.save_chain()
        self.assert_refused_without_writes("seq")

    def test_malformed_json_and_non_objects_are_diagnostics_not_tracebacks(self):
        for raw in ("{", "[]", "null",
                    '{"spec":"rapp-frame/2.0","spec":"rapp/1"}'):
            with self.subTest(raw=raw):
                (self.repo / "frames" / "1.json").write_text(raw, encoding="utf-8")
                before = self.snapshot()
                for main in (pulse_verify.main, pulse_sign.main):
                    result, output = self.run_main(main)
                    self.assertNotEqual(result, 0, output)
                    self.assertIn("1.json", output)
                    self.assertNotIn("Traceback", output)
                self.assertEqual(self.snapshot(), before)

    def test_feed_head_must_be_current_wave_not_particle_or_legacy_alias(self):
        feed = current_feed(self.frames)
        cases = [
            {**feed, "head_hash": self.frames[-1]["payload_hash"]},
            {key: val for key, val in feed.items() if key != "head_hash"},
            {**feed, "head_sha": self.frames[-1]["payload_hash"]},
            {**feed, "spec": "rapp-frame/2.0"},
            {**feed, "stream_id": "rappid:@other/twin:" + "a" * 64},
            {**feed, "count": True},
            current_feed(self.frames[:-1]),
            current_feed([]),
        ]
        for invalid in cases:
            with self.subTest(feed=invalid):
                self.dump(self.repo / "feed.json", invalid)
                result, output = self.verify()
                self.assertNotEqual(result, 0, output)
                self.assertIn("feed", output)

    def test_feed_malformed_json_and_shapes_are_diagnostics(self):
        for raw in ("{", "[]", '{"spec":"rapp/1","frames":null}'):
            with self.subTest(raw=raw):
                (self.repo / "feed.json").write_text(raw, encoding="utf-8")
                result, output = self.verify()
                self.assertNotEqual(result, 0, output)
                self.assertIn("feed.json", output)

    def test_feed_window_is_exactly_the_latest_64_frames(self):
        self.frames = []
        for seq in range(pl.N + 3):
            self.frames.append(current_frame(
                seq, self.frames[-1] if self.frames else None))
        self.save_chain()
        self.assertEqual(pl.build_feed(self.frames), current_feed(self.frames))
        result, output = self.verify()
        self.assertEqual(result, 0, output)
        feed = current_feed(self.frames)
        feed["frames"] = feed["frames"][1:]
        feed["count"] -= 1
        self.dump(self.repo / "feed.json", feed)
        result, output = self.verify()
        self.assertNotEqual(result, 0, output)
        self.assertIn("window", output)

    def test_optional_signing_refuses_legacy_keys_without_creating_or_reading_them(self):
        before = self.snapshot()
        result, output = self.run_main(
            pulse_sign.main, "--sign", "--allow-empty")
        self.assertNotEqual(result, 0, output)
        self.assertIn("JWS", output)
        self.assertEqual(self.snapshot(), before)
        (self.repo / "keys").mkdir()
        (self.repo / "keys" / "pulse.ed25519.key").write_text(
            "not a key; must not be read", encoding="utf-8")
        before = self.snapshot()
        result, output = self.run_main(pulse_sign.main, "--allow-empty")
        self.assertNotEqual(result, 0, output)
        self.assertIn("JWS", output)
        self.assertEqual(self.snapshot(), before)
        result, output = self.sign("--allow-empty")
        self.assertEqual(result, 0, output)

    def test_present_current_signatures_are_not_reported_as_verified(self):
        for sig in ({"alg": "ed25519", "sig": "00" * 64}, "e30..AA"):
            with self.subTest(sig=sig):
                self.frames[1]["sig"] = sig
                self.save_chain()
                self.assert_refused_without_writes("JWS")

    def test_invalid_or_backwards_mint_timestamp_does_not_write(self):
        for utc in ("not-a-date", "2026-02-30T00:00:00Z",
                    "2025-12-31T00:00:00Z", "2026-01-01T00:00:60Z"):
            with self.subTest(utc=utc):
                before = self.snapshot()
                result, output = self.sign("--allow-empty", "--ts", utc)
                self.assertNotEqual(result, 0, output)
                self.assertIn("utc", output)
                self.assertEqual(self.snapshot(), before)

    def test_published_frame_path_cannot_be_overwritten(self):
        before = self.snapshot()
        with self.assertRaises(FileExistsError):
            pl.write_frame(str(self.repo), self.frames[0])
        self.assertEqual(self.snapshot(), before)

    def test_cli_entrypoints_work_offline_without_private_keys(self):
        env = dict(os.environ)
        env.pop("PULSE_TS", None)
        commands = [
            ("pulse_sign.py", ["--no-sign", "--allow-empty",
                               "--ts", "2026-01-01T00:00:02Z"]),
            ("pulse_verify.py", ["--quiet"]),
        ]
        for script, flags in commands:
            result = subprocess.run(
                [sys.executable, str(REPO / "scripts" / script),
                 "--repo", str(self.repo), *flags],
                capture_output=True, text=True, env=env, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / "keys").exists())


if __name__ == "__main__":
    unittest.main()
