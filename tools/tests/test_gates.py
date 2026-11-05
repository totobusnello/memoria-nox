#!/usr/bin/env python3
"""Negative tests for tools/privacy-gate.py and tools/provenance.py.

Each gate must pass a clean state and FAIL a planted offender. Every test builds a throwaway git
repository in a temporary directory; nothing here reads the real corpus or the real term list.

  python3 -I tools/tests/test_gates.py
"""
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

TOOLS = pathlib.Path(__file__).resolve().parent.parent
GATE = TOOLS / "privacy-gate.py"
PROV = TOOLS / "provenance.py"
# offenders are assembled from pieces so this file does not trip the gate when committed
VAULT = "memory/" + "mac-docs/" + "Contrato-Exemplo.pdf"
EVENT = "events/" + "mac/" + "2026-01-01-nota.md"
PERSON = "memory/" + "entities/" + "people/" + "fulano-de-tal"
HOST = "srv" + "123456"
TAILNET = "100." + "92.1.2"
TERM = "zyxquor ventures"


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = pathlib.Path(self.tmp.name)
        run(["git", "init", "-q"], self.p)
        run(["git", "config", "user.email", "t@example.org"], self.p)
        run(["git", "config", "user.name", "t"], self.p)
        self.terms = self.p.parent / (self.p.name + "-terms.sha256")
        h = hashlib.sha256(TERM.encode()).hexdigest()[:16]
        self.terms.write_text(f"# test\n{h}\n")
        self.env = {"PRIVACY_TERMS_FILE": str(self.terms)}

    def write(self, name, text):
        f = self.p / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(text) if isinstance(text, bytes) else f.write_text(text)
        run(["git", "add", name], self.p)

    def commit(self):
        run(["git", "commit", "-qm", "c", "--no-verify"], self.p)

    def gate(self, extra=None):
        return run([sys.executable, "-I", str(GATE), "--staged"], self.p, {**self.env, **(extra or {})})

    def close(self):
        self.terms.unlink(missing_ok=True)
        self.tmp.cleanup()


class PrivacyGate(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_clean_passes(self):
        self.r.write("a.md", "The vault directory memory/mac-docs/ is private; see the gate.\n")
        self.assertEqual(self.r.gate().returncode, 0)

    def test_each_offender_blocks(self):
        # a fresh repository per offender: in a repository with no commit `git reset` does not
        # unstage, and a leftover staged offender would make every later case pass by itself
        # (the mutation run of 2026-11-04 caught exactly that).
        for bad in [VAULT, EVENT, PERSON, HOST, TAILNET, "Deal with Zyxquor Ventures."]:
            with self.subTest(bad=bad):
                r = Repo()
                try:
                    r.write("f.md", f"line before\nsee {bad}\n")
                    res = r.gate()
                    self.assertEqual(res.returncode, 1, res.stderr)
                    self.assertEqual(res.stderr.count("BLOCK"), 1, res.stderr)
                finally:
                    r.close()

    def test_old_content_does_not_block_new_lines(self):
        self.r.write("old.md", f"legacy {HOST}\n")
        self.r.commit()
        self.r.write("old.md", f"legacy {HOST}\nnew clean line\n")
        self.assertEqual(self.r.gate().returncode, 0)

    def test_zip_member_is_scanned(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("inner/rows.json", json.dumps({"source_file": VAULT}))
        self.r.write("pkg.zip", buf.getvalue())
        self.assertEqual(self.r.gate().returncode, 1)

    def test_escape_hatch_needs_a_reason(self):
        self.r.write("x.md", f"{HOST}\n")
        self.assertEqual(self.r.gate({"PRIVACY_GATE_OK": ""}).returncode, 1)
        res = self.r.gate({"PRIVACY_GATE_OK": "fixture, not a real host"})
        self.assertEqual(res.returncode, 0)
        self.assertIn("fixture, not a real host", res.stderr)

    def test_home_path_only_warns(self):
        self.r.write("h.md", "/" + "Users/someone/x\n")
        res = self.r.gate()
        self.assertEqual(res.returncode, 0)
        self.assertIn("WARN", res.stderr)


class Provenance(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.write("audits/a.md", "fidelity 0.900 (135/150); first figure 0.833\n")
        self.r.commit()
        self.sha = run(["git", "rev-parse", "--short", "HEAD"], self.r.p).stdout.strip()
        self.claims = [
            {"id": "fid-old", "value": "0.833", "population": "150", "date": "2026-10-22",
             "artifact": "audits/a.md", "locator": "0.833", "commit": self.sha,
             "superseded_by": "fid"},
            {"id": "fid", "value": "0.900", "population": "150", "date": "2026-10-23",
             "artifact": "audits/a.md", "locator": "0.900", "commit": self.sha,
             "superseded_by": None}]

    def tearDown(self):
        self.r.close()

    def check(self, text, claims=None, ignore=("2026",)):
        d = self.r.p / "paper"
        d.mkdir(exist_ok=True)
        (d / "P.md").write_text(text)
        (d / "PROVENANCE.json").write_text(json.dumps(
            {"text": ["P.md"], "ignore": list(ignore), "claims": claims or self.claims}))
        return run([sys.executable, "-I", str(PROV), "--check", str(d)], self.r.p)

    def test_current_claim_passes(self):
        self.assertEqual(self.check("Fidelity was 0.900 in 2026.\n").returncode, 0)

    def test_superseded_value_fails(self):
        res = self.check("Fidelity was 0.833.\n")
        self.assertEqual(res.returncode, 1)
        self.assertIn("superseded", res.stderr)

    def test_unclaimed_number_fails(self):
        self.assertEqual(self.check("Fidelity was 0.900, recall 0.71.\n").returncode, 1)

    def test_missing_locator_fails(self):
        c = [dict(self.claims[1], locator="0.999")]
        self.assertEqual(self.check("Fidelity 0.900.\n", claims=c).returncode, 1)

    def test_unknown_commit_fails(self):
        c = [dict(self.claims[1], commit="deadbeef")]
        self.assertEqual(self.check("Fidelity 0.900.\n", claims=c).returncode, 1)

    def test_numbers_in_code_are_ignored(self):
        self.assertEqual(self.check("Run `tool --x 3.14` then 0.900.\n").returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
