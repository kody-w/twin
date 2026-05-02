"""Tests for utils/lineage_check.py — covers all status branches."""

import json
import pathlib
import shutil
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "utils"))

import lineage_check  # noqa: E402


def _make_repo(tmp: pathlib.Path, rappid_data: dict, git_remote: str = ""):
    """Create a fake repo with rappid.json + a fake git remote (no actual git operations)."""
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "rappid.json").write_text(json.dumps(rappid_data, indent=2))
    # Mock the git remote by writing a fake .git/config.
    git_dir = tmp / ".git"
    git_dir.mkdir(exist_ok=True)
    cfg = "[core]\n    repositoryformatversion = 0\n"
    if git_remote:
        cfg += f'[remote "origin"]\n    url = {git_remote}\n    fetch = +refs/heads/*:refs/remotes/origin/*\n'
    (git_dir / "config").write_text(cfg)


class TestNoRappid(unittest.TestCase):
    def test_no_rappid_json_returns_no_rappid(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "no_rappid")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSelfTemplateRoot(unittest.TestCase):
    def test_wildhaven_at_correct_remote_returns_self(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_rappid": "0b635450-c042-49fb-b4b1-bdb571044dec",
                "parent_repo": "https://github.com/kody-w/RAPP.git",
                "name": "wildhaven-ai-homes-twin",
                "role": "variant",
            }, git_remote="https://github.com/kody-w/wildhaven-ai-homes-twin.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "self")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rapp_at_correct_remote_returns_self(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "0b635450-c042-49fb-b4b1-bdb571044dec",
                "parent_rappid": None,
                "parent_repo": None,
                "name": "rapp",
                "role": "master",
            }, git_remote="https://github.com/kody-w/RAPP.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "self")


        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestUninitializedTemplateClone(unittest.TestCase):
    def test_wildhaven_rappid_at_different_remote(self):
        """rappid is wildhaven's, but git remote is somewhere else → uninitialized."""
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_rappid": "0b635450-c042-49fb-b4b1-bdb571044dec",
                "parent_repo": "https://github.com/kody-w/RAPP.git",
                "name": "wildhaven-ai-homes-twin",
                "role": "variant",
            }, git_remote="https://github.com/someone-else/cloned-it.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "variant_uninitialized")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestVariantInitialized(unittest.TestCase):
    def test_unique_rappid_with_proper_parent(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "99999999-aaaa-bbbb-cccc-dddddddddddd",
                "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_repo": "https://github.com/kody-w/wildhaven-ai-homes-twin.git",
                "name": "my-variant",
                "role": "variant",
            }, git_remote="https://github.com/me/my-variant.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "variant_initialized")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestLineageMismatch(unittest.TestCase):
    def test_variant_has_no_parent_repo(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "deadbeef-0000-1111-2222-333333333333",
                "parent_rappid": None,
                "parent_repo": None,
                "name": "orphan",
                "role": "variant",
            }, git_remote="https://github.com/me/orphan.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "lineage_mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_variant_parent_repo_equals_self_remote(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "feedface-0000-1111-2222-333333333333",
                "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_repo": "https://github.com/me/myself.git",
                "name": "self-parent",
                "role": "variant",
            }, git_remote="https://github.com/me/myself.git")
            info = lineage_check.check_lineage(tmp)
            self.assertEqual(info["status"], "lineage_mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAssertInitialized(unittest.TestCase):
    def test_uninitialized_raises_systemexit(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_rappid": "0b635450-c042-49fb-b4b1-bdb571044dec",
                "parent_repo": "https://github.com/kody-w/RAPP.git",
                "name": "wildhaven-ai-homes-twin",
                "role": "variant",
            }, git_remote="https://github.com/me/cloned.git")
            with self.assertRaises(SystemExit):
                lineage_check.assert_initialized(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_initialized_returns_info(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            _make_repo(tmp, {
                "schema": "rapp-rappid/1.1",
                "rappid": "abcdef00-1111-2222-3333-444444444444",
                "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
                "parent_repo": "https://github.com/kody-w/wildhaven-ai-homes-twin.git",
                "name": "good-variant",
                "role": "variant",
            }, git_remote="https://github.com/me/good-variant.git")
            info = lineage_check.assert_initialized(tmp)
            self.assertEqual(info["status"], "variant_initialized")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestNormalizeOwnerRepo(unittest.TestCase):
    def test_https_form(self):
        self.assertEqual(
            lineage_check._normalize_owner_repo("https://github.com/kody-w/RAPP.git"),
            "kody-w/rapp",
        )

    def test_ssh_form(self):
        self.assertEqual(
            lineage_check._normalize_owner_repo("git@github.com:kody-w/RAPP.git"),
            "kody-w/rapp",
        )

    def test_no_dot_git(self):
        self.assertEqual(
            lineage_check._normalize_owner_repo("https://github.com/kody-w/twin"),
            "kody-w/twin",
        )

    def test_empty(self):
        self.assertEqual(lineage_check._normalize_owner_repo(""), "")
        self.assertEqual(lineage_check._normalize_owner_repo(None or ""), "")


if __name__ == "__main__":
    unittest.main()
