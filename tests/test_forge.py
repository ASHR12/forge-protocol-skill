import json
import unittest

from helpers import Project, call, forge, verdict

import forgelib as fl


class InitTests(unittest.TestCase):
    def test_modes_scaffold_different_documents(self):
        expected = {"sprint": {"BRIEF.md", "art/BAR.md"},
                    "standard": {"BRIEF.md", "PLAN.md", "art/BAR.md", "art/LOOK.md"},
                    "forge": {"BRIEF.md", "PLAN.md", "art/BAR.md", "art/LOOK.md", "art/LEDGER.md"}}
        for mode, docs in expected.items():
            with self.subTest(mode=mode):
                project = Project(mode=mode, publish=False)
                try:
                    present = {p for p in ("BRIEF.md", "PLAN.md", "art/BAR.md", "art/LOOK.md", "art/LEDGER.md")
                               if project.path(p).is_file()}
                    self.assertEqual(present, docs)
                    cfg = json.loads(project.path("forge.json").read_text())
                    self.assertEqual(cfg["budgets"], forge.MODES[mode])
                    brief = project.path("BRIEF.md").read_text()
                    self.assertIn("Publish: LOCKED", brief)
                    self.assertNotIn("{{", brief)
                finally:
                    project.close()

    def test_init_refuses_existing_project_and_keeps_files(self):
        project = Project(publish=False)
        try:
            project.path("BRIEF.md").write_text("mine")
            code, _, err = project.forge("init", "--title", "Again")
            self.assertEqual(code, 1)
            self.assertIn("already exists", err)
            self.assertEqual(project.path("BRIEF.md").read_text(), "mine")
        finally:
            project.close()

    def test_budget_overrides_and_web_capture_template(self):
        project = Project(publish=False)
        try:
            root = project.root.parent / "web"
            code, _, err = call(forge.main, ["--project", str(root), "init", "--mode", "sprint", "--title", "W",
                                             "--stack", "web", "--rounds", "5", "--minutes", "0"])
            self.assertEqual(code, 0, err)
            cfg = json.loads((root / "forge.json").read_text())
            self.assertEqual((cfg["budgets"]["rounds"], cfg["budgets"]["minutes"]), (5, 0))
            self.assertTrue((root / "tools" / "capture.mjs").is_file())
        finally:
            project.close()


class LogTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def events(self):
        return fl.read_log(self.p.path("artifacts/rounds.log"))

    def test_event_line_round_trips(self):
        line = fl.format_event("2026-10-05T12:00:00+05:30", {"stage": "loop", "round": "R01", "role": "critic",
                                                            "result": "FAIL"}, {"rung": 2}, note="a | b\nc")
        ev = fl.parse_log(line + "\n    | continuation\n")[0]
        self.assertEqual((ev["stage"], ev["round"], ev["result"], ev["rung"]), ("loop", "R01", "FAIL", "2"))
        self.assertEqual(ev["note"], "a / b c")
        self.assertEqual(ev["continuation"], ["| continuation"])

    def test_capture_records_round_bar_and_hash(self):
        self.p.capture()
        ev = self.events()[-1]
        self.assertEqual((ev["result"], ev["round"], ev["bar"]), ("CAPTURE", "R01", "v1"))
        self.assertEqual(ev["barsha"], fl.text_sha(self.p.path("art/BAR.md").read_text()))
        self.assertNotEqual(ev["build"], "n/a")

    def test_round_rules(self):
        code, _, err = self.p.forge("log", "--result", "FAIL")
        self.assertEqual(code, 1, "verdict without an open round must be refused")
        self.p.capture()
        code, _, err = self.p.forge("log", "--result", "CAPTURE")
        self.assertEqual(code, 1)
        self.assertIn("still open", err)
        code, _, err = self.p.forge("log", "--result", "FAIL", "--round", "R07")
        self.assertEqual(code, 1)
        self.assertEqual(self.p.forge("log", "--result", "FAIL", "--role", "critic")[0], 0)
        self.p.capture()
        self.assertEqual(self.events()[-1]["round"], "R02")

    def test_recapture_keeps_the_round_number(self):
        self.p.capture()
        self.assertEqual(self.p.forge("log", "--result", "RECAPTURE", "--role", "critic")[0], 0)
        self.p.capture()
        self.assertEqual(self.events()[-1]["round"], "R01")

    def test_unknown_result_and_reserved_fields(self):
        self.assertEqual(self.p.forge("log", "--result", "DONE")[0], 2)
        self.assertEqual(self.p.forge("log", "--result", "NOTE", "--field", "round=R9")[0], 2)


class BarRatchetTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.bar = self.p.path("art/BAR.md")

    def tearDown(self):
        self.p.close()

    def edit(self, old, new):
        text = self.bar.read_text()
        self.assertIn(old, text)
        self.bar.write_text(text.replace(old, new))

    def fail_round(self, c5="FAIL"):
        build = self.p.capture()
        self.p.path("artifacts/verdicts/R01.md").write_text(verdict("FAIL", "R01", build, c5=c5, c4="FAIL"))
        self.assertEqual(self.p.forge("log", "--result", "FAIL", "--role", "critic")[0], 0)

    def test_initial_publish_writes_history_and_version(self):
        self.assertIn("BAR-VERSION: v1", self.bar.read_text())
        self.assertTrue(self.p.path("art/bar-history/BAR-v1.md").is_file())
        ev = [e for e in fl.read_log(self.p.path("artifacts/rounds.log")) if e["result"] == "BAR-PUBLISH"][0]
        self.assertEqual((ev["type"], ev["criteria"]), ("initial", "5"))
        self.assertTrue(any("C5 Lighting and depth" in line for line in ev["continuation"]))

    def test_placeholder_and_image_relative_criteria_are_refused(self):
        p = Project(publish=False)
        try:
            bar = p.path("art/BAR.md")
            bar.write_text(bar.read_text().split("## C4")[0] + "## C4 <name>\n- PASS when: <observable condition>\n")
            code, _, err = p.forge("bar", "publish", "--reason", "x")
            self.assertEqual(code, 2)
            self.assertIn("placeholder", err)
            bar.write_text(bar.read_text().replace("## C4 <name>\n- PASS when: <observable condition>",
                                                   "## C4 Hero look\n- PASS when: the hero looks like the reference shot."))
            code, _, err = p.forge("bar", "publish", "--reason", "x")
            self.assertEqual(code, 1)
            self.assertIn("observable quality", err)
        finally:
            p.close()

    def test_revisions_only_between_rounds(self):
        self.p.capture()
        self.edit("a rim that separates", "a crisp rim that separates")
        code, _, err = self.p.forge("bar", "publish", "--type", "raise", "--reason", "sharper rim")
        self.assertEqual(code, 1)
        self.assertIn("open", err)

    def test_unpublished_edits_block_capture(self):
        self.edit("a rim that separates", "a crisp rim that separates")
        code, _, err = self.p.forge("log", "--result", "CAPTURE")
        self.assertEqual(code, 1)
        self.assertIn("unpublished", err)

    def test_add_and_raise_are_logged_with_diff(self):
        self.bar.write_text(self.bar.read_text() + "\n## C6 Glance read\n- PASS when: blurred, each still keeps one clear focal point.\n")
        self.assertEqual(self.p.forge("bar", "publish", "--type", "add", "--reason", "squint test")[0], 0)
        ev = fl.read_log(self.p.path("artifacts/rounds.log"))[-1]
        self.assertEqual((ev["bar"], ev["type"], ev["audit"]), ("v2", "add", "none"))
        self.assertTrue(any(line.startswith("| +## C6 Glance read") for line in ev["continuation"]))
        self.assertTrue(self.p.path("art/bar-history/BAR-v2.md").is_file())

    def test_add_type_rejects_edits(self):
        self.edit("a rim that separates", "a crisp rim that separates")
        self.assertEqual(self.p.forge("bar", "publish", "--type", "add", "--reason", "x")[0], 1)

    def test_raising_a_failing_criterion_needs_an_audit(self):
        self.fail_round()
        self.edit("a rim that separates", "a crisp rim that separates")
        self.assertEqual(self.p.forge("bar", "publish", "--type", "raise", "--reason", "sharper rim")[0], 0)
        self.assertEqual(fl.read_log(self.p.path("artifacts/rounds.log"))[-1]["audit"], "pending")
        code, _, err = self.p.forge("log", "--result", "CAPTURE")
        self.assertEqual(code, 1)
        self.assertIn("audit", err)
        self.assertEqual(self.p.forge("log", "--result", "BAR-OK", "--role", "critic")[0], 0)
        self.assertEqual(self.p.forge("log", "--result", "CAPTURE")[0], 0)

    def test_bar_lowered_blocks_capture(self):
        self.fail_round()
        self.edit("a rim that separates", "a rim near")
        self.assertEqual(self.p.forge("bar", "publish", "--type", "clarify", "--reason", "wording")[0], 0)
        self.assertEqual(self.p.forge("log", "--result", "BAR-LOWERED", "--role", "critic")[0], 0)
        code, _, err = self.p.forge("log", "--result", "CAPTURE")
        self.assertEqual(code, 1)
        self.assertIn("BAR-LOWERED", err)

    def test_retire_and_loosen_need_user_approval(self):
        self.bar.write_text(self.bar.read_text().split("## C5")[0])
        for kind in ("raise", "clarify", "retire"):
            self.assertEqual(self.p.forge("bar", "publish", "--type", kind, "--reason", "drop C5")[0], 1, kind)
        code, _, err = self.p.forge("bar", "publish", "--type", "retire", "--reason", "user cut lighting",
                                    "--user-approved", "drop the lighting criterion, it's a flat UI")
        self.assertEqual(code, 0, err)
        ev = fl.read_log(self.p.path("artifacts/rounds.log"))[-1]
        self.assertEqual(ev["approved"], "drop the lighting criterion, it's a flat UI")

    def test_no_change_is_a_noop(self):
        code, out, _ = self.p.forge("bar", "publish", "--type", "raise", "--reason", "x")
        self.assertEqual(code, 0)
        self.assertIn("nothing to publish", out)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.p = Project(mode="sprint")

    def tearDown(self):
        self.p.close()

    def round(self, n, c5):
        build = self.p.capture(shade=60 + n)
        label = fl.round_label(n)
        self.p.path(f"artifacts/verdicts/{label}.md").write_text(verdict("FAIL", label, build, c5=c5, c4="PASS"))
        self.assertEqual(self.p.forge("log", "--result", "FAIL", "--role", "critic")[0], 0)

    def status(self):
        code, out, _ = self.p.forge("status", "--json")
        self.assertEqual(code, 0)
        return json.loads(out)

    def test_streaks_trigger_diagnosis_and_reset_after_steer(self):
        self.round(1, "FAIL")
        self.assertFalse(self.status()["diagnose_due"])
        self.round(2, "FAIL")
        status = self.status()
        self.assertTrue(status["diagnose_due"])
        self.assertEqual(status["stuck_criteria"], ["C5"])
        self.assertIn("Diagnoser", status["next"])
        self.p.forge("log", "--result", "DIAGNOSE-STEER", "--round", "R02")
        self.assertFalse(self.status()["diagnose_due"])

    def test_budget_exhaustion_and_extension(self):
        for n in (1, 2, 3):
            self.round(n, "PASS" if n == 2 else "FAIL")
        status = self.status()
        self.assertTrue(status["budget_exhausted"])
        self.assertEqual(status["rounds_used"], 3)
        self.assertIn("budget exhausted", status["next"])
        self.p.forge("log", "--result", "BUDGET-EXTENDED", "--role", "user", "--field", "rounds=+2")
        self.assertFalse(self.status()["budget_exhausted"])

    def test_unchanged_build_is_flagged(self):
        self.round(1, "FAIL")
        self.round(2, "PASS")
        self.assertTrue(self.status()["build_unchanged"])

    def test_snapshot(self):
        self.p.capture()
        code, out, err = self.p.forge("snapshot", "R1")
        self.assertEqual(code, 0, err)
        self.assertTrue(self.p.path("artifacts/history/R01/still-01.png").is_file())
        self.assertTrue(self.p.path("artifacts/history/R01/MANIFEST.md").is_file())
        self.assertEqual(self.p.forge("snapshot", "R01")[0], 2)


if __name__ == "__main__":
    unittest.main()
