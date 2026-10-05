import unittest

from helpers import Project, run_script, verdict

import validate_verdict as vv


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.build = self.p.capture()

    def tearDown(self):
        self.p.close()

    def check(self, text, **kw):
        return vv.validate(text, self.p.root, **kw)

    def assertInvalid(self, text, fragment, **kw):
        result = self.check(text, **kw)
        self.assertFalse(result["valid"], f"expected invalid ({fragment})")
        self.assertTrue(any(fragment in e for e in result["errors"]), result["errors"])

    def test_good_win_and_fail(self):
        win = self.check(verdict("WIN", "R01", self.build))
        self.assertTrue(win["valid"], win["errors"])
        fail = self.check(verdict("FAIL", "R01", self.build, c5="FAIL"))
        self.assertTrue(fail["valid"], fail["errors"])

    def test_cli_exit_codes(self):
        path = self.p.path("artifacts/verdicts/R01.md")
        path.write_text(verdict("WIN", "R01", self.build))
        self.assertEqual(run_script("validate_verdict.py", str(path), "--project", str(self.p.root)).returncode, 0)
        path.write_text(verdict("WIN", "R01", self.build, c5="FAIL"))
        res = run_script("validate_verdict.py", str(path), "--project", str(self.p.root), "--json")
        self.assertEqual(res.returncode, 1)
        self.assertIn('"valid": false', res.stdout)
        self.assertEqual(run_script("validate_verdict.py", "/no/such/file", "--project", str(self.p.root)).returncode, 2)
        res = run_script("validate_verdict.py", "-", "--project", str(self.p.root), stdin=verdict("WIN", "R01", self.build))
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_win_with_a_fail_is_invalid(self):
        self.assertInvalid(verdict("WIN", "R01", self.build, c5="FAIL"), "WIN with non-PASS")

    def test_fail_needs_matching_punch_items(self):
        text = verdict("FAIL", "R01", self.build, c5="FAIL").split("PUNCH LIST:")[0]
        self.assertInvalid(text, "without a PUNCH LIST")
        text = verdict("FAIL", "R01", self.build, c5="FAIL").replace("Done when still-03", "Fixed if still-03")
        self.assertInvalid(text, "Done when")
        text = verdict("FAIL", "R01", self.build, c4="FAIL", c5="FAIL")
        text = "\n".join(line for line in text.splitlines() if not line.startswith("2. "))
        self.assertInvalid(text, "C5 FAILs but has no punch item")

    def test_every_criterion_once_and_known(self):
        text = verdict("WIN", "R01", self.build)
        self.assertInvalid("\n".join(l for l in text.splitlines() if not l.startswith("C3 ")), "not graded: C3")
        self.assertInvalid(text + "C9 Extra: PASS. still-01 shows extra things here.\n", "C9 is not in art/BAR.md")
        dup = text.replace("CRITERIA:\n", "CRITERIA:\nC1 Goal fit: PASS. still-01 shows the hero clearly again.\n")
        self.assertInvalid(dup, "graded 2 times")

    def test_stills_must_all_be_cited_and_exist(self):
        text = verdict("WIN", "R01", self.build).replace("still-01, still-02, still-03", "still-01, still-03")
        self.assertInvalid(text, "still not cited: still-02")
        self.assertInvalid(verdict("WIN", "R01", self.build).replace("still-03 orb", "still-07 orb"), "still-07, which does not exist")
        self.assertInvalid(verdict("WIN", "R01", self.build).replace("frame-01, frame-02 show", "the walkthrough shows"),
                           "none are cited")

    def test_banned_phrases_scores_and_identifiers(self):
        base = verdict("WIN", "R01", self.build)
        self.assertInvalid(base.replace("dominates clearly", "is close enough"), "close enough")
        self.assertInvalid(base.replace("dominates clearly", "dominates, 8/10"), "8/10")
        self.assertInvalid(base.replace("dominates clearly", "dominates (grade: A-)"), "letter grade")
        self.assertInvalid(base.replace("dominates clearly", "dominates, 90% polished"), "percentage")
        self.assertInvalid(base.replace("dominates clearly", "dominates as GPT-5 would want"), "identifier")
        allowed = self.check(base.replace("dominates clearly", "dominates as GPT-5 would want"), allow_identifiers=True)
        self.assertTrue(allowed["valid"], allowed["errors"])
        measurement = self.check(base.replace("dominates clearly", "dominates and fills 40% of the frame width"))
        self.assertTrue(measurement["valid"], measurement["errors"])
        self.assertTrue(measurement["warnings"])

    def test_resolution_numbers_are_not_scores(self):
        result = self.check(verdict("WIN", "R01", self.build).replace("for still-01", "at 1920x1080 for still-01"))
        self.assertTrue(result["valid"], result["errors"])

    def test_stale_bar_version_is_rejected(self):
        self.assertInvalid(verdict("WIN", "R01", self.build, bar_version=2), "bar v2 but art/BAR.md is v1")
        self.assertInvalid(verdict("WIN", "R01", self.build).replace("(5 criteria)", "(4 criteria)"), "4 criteria")

    def test_bar_edited_mid_round_is_rejected(self):
        bar = self.p.path("art/BAR.md")
        bar.write_text(bar.read_text().replace("a rim that separates", "a faint rim near"))
        self.assertInvalid(verdict("WIN", "R01", self.build), "changed after the R01 CAPTURE")

    def test_build_and_manifest_consistency(self):
        self.assertInvalid(verdict("WIN", "R01", "deadbee"), "BUILD deadbee")
        manifest = self.p.path("artifacts/stills/MANIFEST.md")
        lines = manifest.read_text().splitlines()
        lines[-1] = lines[-1].replace(self.build, "otherbuild")
        manifest.write_text("\n".join(lines) + "\n")
        self.assertInvalid(verdict("WIN", "R01", self.build), "mixes builds")
        manifest.unlink()
        self.assertInvalid(verdict("WIN", "R01", self.build), "MANIFEST.md missing")
        fail = self.check(verdict("FAIL", "R01", self.build, c5="FAIL"))
        self.assertTrue(fail["valid"], fail["errors"])
        self.assertTrue(any("MANIFEST" in w for w in fail["warnings"]))

    def test_round_must_have_a_capture(self):
        self.assertInvalid(verdict("WIN", "R05", self.build), "no CAPTURE for R05")

    def test_schema_basics(self):
        self.assertInvalid("Looks great overall.\n", "no 'VERDICT")
        self.assertInvalid("VERDICT: PASS\n", "unknown verdict type")
        self.assertInvalid(verdict("WIN", "R01", self.build).replace("SCOPE: loop", "SCOPE: gate"), "not valid for SCOPE gate")
        self.assertInvalid(verdict("WIN", "R01", self.build), "expected SCOPE plan", scope="plan")
        fenced = "```\n" + verdict("WIN", "R01", self.build) + "```\n"
        self.assertTrue(self.check(fenced)["valid"])

    def test_other_scopes(self):
        good = {
            "GATE-PASS": f"VERDICT: GATE-PASS\nSCOPE: gate\nCOMPONENT: hero orb\nBUILD: {self.build}\nBAR: v1 (5 criteria)\n"
                         "CRITERIA:\nC5 Lighting and depth: PASS. The gate capture shows a lit side and a rim.\n",
            "PLAN-OK": "VERDICT: PLAN-OK\nSCOPE: plan\nBAR: v1 (5 criteria)\n",
            "PLAN-GAPS": "VERDICT: PLAN-GAPS\nSCOPE: plan\nBAR: v1 (5 criteria)\n1. C5 needs a lighting rig the plan never builds.\n",
            "BAR-OK": "VERDICT: BAR-OK\nSCOPE: bar\nBAR: v1 (5 criteria)\n",
            "BAR-LOWERED": "VERDICT: BAR-LOWERED\nSCOPE: bar\nBAR: v1 (5 criteria)\n1. C5 dropped the rim requirement, so a flat orb now passes.\n",
            "RECAPTURE": "VERDICT: RECAPTURE\nSCOPE: loop\nROUND: R01\n1. still-02 is 800x600; BRIEF asks for 1920x1080.\n",
            "AB": "VERDICT: AB\nSCOPE: ab\nPAIR 01: B. B shows a lit orb with a rim and a glow.\nOVERALL: B\n",
            "BLOCKED": "VERDICT: BLOCKED\nREASON: the image viewer could not open any still.\n",
        }
        for kind, text in good.items():
            with self.subTest(kind=kind):
                result = self.check(text)
                self.assertTrue(result["valid"], result["errors"])
        self.assertInvalid("VERDICT: BAR-LOWERED\nSCOPE: bar\nBAR: v1 (5 criteria)\n1. it got easier.\n", "must name the criterion")
        self.assertInvalid("VERDICT: AB\nSCOPE: ab\nPAIR 01: A. A is better in R02 terms.\n", "OVERALL")
        self.assertInvalid("VERDICT: BLOCKED\n", "REASON")
        self.assertInvalid("VERDICT: RECAPTURE\nSCOPE: loop\nROUND: R01\n", "numbered list")
        self.assertInvalid(good["GATE-PASS"].replace("COMPONENT: hero orb\n", ""), "COMPONENT")


if __name__ == "__main__":
    unittest.main()
