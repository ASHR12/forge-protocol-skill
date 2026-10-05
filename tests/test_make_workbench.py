import re
import unittest

from helpers import Project, call, verdict

import make_workbench


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def build(self):
        code, out, err = call(make_workbench.main, ["--project", str(self.p.root), "--refresh", "15"])
        self.assertEqual(code, 0, err)
        return self.p.path("artifacts/workbench.html").read_text()

    def test_empty_project_renders(self):
        page = self.build()
        self.assertIn("<title>Orb Page | workbench</title>", page)
        self.assertIn("No captures yet", page)
        self.assertIn("refreshMs = 15 * 1000", page)

    def test_rounds_matrix_slider_and_escaping(self):
        for n, c5 in ((1, "FAIL"), (2, "PASS")):
            build = self.p.capture(shade=50 + 40 * n)
            label = f"R{n:02d}"
            text = verdict("FAIL" if c5 == "FAIL" else "WIN", label, build, c5=c5)
            if c5 == "FAIL":
                text = text.replace("no light direction.", "no light direction <script>alert(1)</script>.")
            self.p.path(f"artifacts/verdicts/{label}.md").write_text(text)
            self.assertEqual(self.p.forge("log", "--result", "FAIL" if c5 == "FAIL" else "WIN", "--role", "critic")[0], 0)
            self.assertEqual(self.p.forge("snapshot", label)[0], 0)
        page = self.build()
        for section in ('id="now"', 'id="progress"', 'id="matrix"', 'id="rounds"', 'id="bar"', 'id="log"'):
            self.assertIn(section, page)
        self.assertIn('class="ba"', page)
        self.assertIn("R02 WIN", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertRegex(page, r'src="stills/still-01\.png\?v=\d+"')
        self.assertRegex(page, r'src="history/R01/still-01\.png\?v=\d+"')
        self.assertEqual(len(re.findall(r'<td class="fail" title="C\d+ R\d+', page)), 1)

    def test_handoff_marks_final_win(self):
        build = self.p.capture()
        self.p.path("artifacts/verdicts/R01.md").write_text(verdict("WIN", "R01", build))
        self.p.forge("log", "--result", "WIN", "--role", "critic")
        self.p.forge("log", "--result", "HANDOFF")
        self.assertIn("FINAL WIN", self.build())

    def test_bad_refresh_is_a_usage_error(self):
        self.assertEqual(call(make_workbench.main, ["--project", str(self.p.root), "--refresh", "1"])[0], 2)


if __name__ == "__main__":
    unittest.main()
