"""RAPP/1 rev-17 conformance of the twin's own primitives (kody-w/rapp-1 @ f6bafe7).

utils/frames.py (canonical form, H), utils/egg.py (rappid grammar, keyless mint) and scripts/pulse_lib.py
(canonical form, H, utc, the strict JSON reader). Pure stdlib; no network, no brainstem.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "utils"))
sys.path.insert(0, str(ROOT / "scripts"))
import egg  # noqa: E402
import frames  # noqa: E402
import pulse_lib as pl  # noqa: E402

TAIL = "0123456789abcdef" * 4


class TestFramesCanonical(unittest.TestCase):
    def test_numbers_follow_rfc8785(self):
        self.assertEqual(frames._canonical({"b": 1.5, "a": [1e21, -0.0, 2 ** 53]}),
                         '{"a":[1e+21,0,9007199254740992],"b":1.5}')
        with self.assertRaises(ValueError):
            frames._canonical(2 ** 53 + 1)

    def test_strings_outside_ijson_are_refused(self):
        for bad in ("\ud800", "\ufffe", "\U0010ffff", "\ufdd0"):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                frames._canonical({"k": bad})

    def test_h_takes_only_value_tags(self):
        self.assertEqual(len(frames._H("rapp/1:particle", {})), 64)
        for tag in ("rapp/1:egg", "rapp/1:rappid", "rapp/1:other", ""):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                frames._H(tag, {})


class TestEggRappid(unittest.TestCase):
    def test_parse_is_whole_string_and_bounded(self):
        self.assertEqual(egg.parse_rappid("rappid:@kody-w/twin:" + TAIL)["hash"], TAIL)
        for bad in ("rappid:@kody-w/twin:" + TAIL + "\n", "rappid:@" + "a" * 40 + "/twin:" + TAIL,
                    "rappid:@kody-w/" + "s" * 101 + ":" + TAIL):
            with self.subTest(bad=bad[:50]):
                self.assertIsNone(egg.parse_rappid(bad))
        self.assertEqual(egg.parse_rappid("rappid:@" + "a" * 39 + "/" + "s" * 100 + ":" + TAIL)["slug"], "s" * 100)

    def test_mint_refuses_labels_instead_of_renaming(self):
        for owner, slug in (("Kody", "twin"), ("kody-w", "my_twin"), ("a" * 40, "twin"), ("kody-w", "")):
            with self.subTest(owner=owner, slug=slug), self.assertRaises(ValueError):
                egg._make_rappid("twin", "@" + owner, slug)
        minted = egg._make_rappid("twin", "@kody-w", "twin")
        self.assertIsNotNone(egg.parse_rappid(minted))

    def test_get_or_create_still_derives_labels_from_free_form_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = egg._IDENTITY_FILE
            egg._IDENTITY_FILE = os.path.join(tmp, "identity.json")
            try:
                twin = egg.get_or_create_twin_rappid(publisher="@Kody_W" + "x" * 50, slug="My Twin!")
                rapp = egg.get_or_create_rapp_rappid("Kanban_Board", publisher="@anon")
            finally:
                egg._IDENTITY_FILE = saved
        self.assertTrue(twin.startswith("rappid:@kody-w" + "x" * 33 + "/my-twin:"))
        self.assertIsNotNone(egg.parse_rappid(twin))
        self.assertTrue(rapp.startswith("rappid:@anon/kanban-board:"))


class TestPulseLibRev17(unittest.TestCase):
    def test_h_tags_and_noncharacters(self):
        with self.assertRaises(ValueError):
            pl.content_hash("rapp/1:egg", {})
        with self.assertRaises(ValueError):
            pl.canonicalize({"k": "\ufffe"})

    def test_utc_years_0000_to_9999(self):
        for good in ("0000-02-29T00:00:00.000Z", "9999-12-31T23:59:59.999Z"):
            pl.validate_utc(good)
        for bad in ("2026-02-29T00:00:00.000Z", "2026-01-01T00:00:60.000Z", "2026-01-01T24:00:00.000Z"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pl.validate_utc(bad)

    def test_reader_refuses_numbers_outside_binary64(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.json")
            for text in ('{"n": 1e400}', '{"n": 9007199254740993}', '{"n": 0.10000000000000001}'):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    pl.load_json(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"n": 1E2}')
            self.assertEqual(pl.canonicalize(pl.load_json(path)), b'{"n":100}')


if __name__ == "__main__":
    unittest.main()
