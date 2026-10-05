import re
import unittest

from helpers import REPO, SKILL, run_script

import forgelib as fl

SKILL_MD = SKILL / "SKILL.md"
DOCS = [SKILL_MD, REPO / "README.md", *sorted((SKILL / "references").glob("*.md")), SKILL / "THIRD_PARTY_NOTICES.md"]
LEFTOVERS = re.compile(
    r"refs-locked|SOURCES\.md|REF \(review only\)|\bparity\b|look-match|\banvil\b|\binspiration\b|reference slot"
    r"|locked reference|\breference (?:image|screenshot|frame|shot)s?\b", re.I)


def frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "SKILL.md must start with YAML frontmatter"
    block = match.group(1)
    keys = re.findall(r"^([A-Za-z][\w-]*):", block, re.M)

    def folded(key):
        m = re.search(rf"^{key}:\s*>-?\n((?:[ ]{{2,}}.*\n?)+)", block + "\n", re.M)
        if m:
            return " ".join(line.strip() for line in m.group(1).splitlines())
        m = re.search(rf"^{key}:\s*(.+)$", block, re.M)
        return m.group(1).strip().strip("'\"") if m else None

    return keys, folded, text[match.end():]


class FrontmatterTests(unittest.TestCase):
    def test_spec_fields(self):
        keys, folded, _ = frontmatter()
        name = folded("name")
        self.assertEqual(name, SKILL.name)
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        description = folded("description")
        self.assertTrue(0 < len(description) <= 1024, len(description))
        self.assertIn("Use when", description)
        self.assertNotRegex(description, r"[<>]")
        self.assertLessEqual(len(folded("compatibility")), 500)
        self.assertTrue(set(keys) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}, keys)
        self.assertIn('version: "2.0.0"', SKILL_MD.read_text(encoding="utf-8").split("---")[1])

    def test_body_size(self):
        _, _, body = frontmatter()
        self.assertLess(SKILL_MD.read_text().count("\n"), 500)
        self.assertRegex(body, r"(?m)^## When to Use")

    def test_no_named_agent_products(self):
        products = re.compile(r"\b(cursor|claude|grok|hermes|codex|antigravity|gemini cli|copilot|opencode)\b", re.I)
        for doc in [SKILL_MD, REPO / "README.md", *sorted((SKILL / "references").glob("*.md"))]:
            for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
                with self.subTest(doc=doc.name, line=n):
                    self.assertIsNone(products.search(line), f"{doc.name}:{n}: {line.strip()}")


class DocsTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        for doc in DOCS:
            for target in re.findall(r"\]\(([^)#\s]+)\)", doc.read_text(encoding="utf-8")):
                if re.match(r"[a-z]+://", target):
                    continue
                with self.subTest(doc=doc.name, target=target):
                    self.assertTrue((doc.parent / target).exists(), f"{doc.name} links to missing {target}")

    def test_no_latex_math(self):
        for doc in [*DOCS, *(SKILL / "templates").glob("*.md")]:
            self.assertNotRegex(doc.read_text(encoding="utf-8"), r"\$\\|\\rightarrow|\\leftrightarrow", doc.name)

    def test_banned_phrases_match_the_validator(self):
        text = (SKILL / "references" / "critic-prompt.md").read_text(encoding="utf-8")
        section = text.split("## Banned soft-pass phrases", 1)[1].split("\n## ", 1)[0]
        listed = set(re.findall(r'"([^"]+)"', section))
        self.assertEqual(listed, set(fl.BANNED_PHRASES))

    def test_no_reference_image_leftovers(self):
        files = [*DOCS, *(SKILL / "templates").iterdir(), *(SKILL / "scripts").glob("*.py")]
        for path in files:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if "RELATIVE_RE = " in line:
                    continue
                with self.subTest(file=path.name, line=n):
                    self.assertIsNone(LEFTOVERS.search(line), f"{path.name}:{n}: {line.strip()}")

    def test_no_stray_files(self):
        self.assertFalse((SKILL / "README.md").exists())
        self.assertEqual(list(REPO.rglob(".DS_Store")), [])

    def test_scripts_named_in_skill_md_exist(self):
        body = SKILL_MD.read_text(encoding="utf-8")
        for script in re.findall(r"`((?:templates/)?[\w]+\.(?:py|mjs))`", body):
            path = SKILL / (script if "/" in script else f"scripts/{script}")
            self.assertTrue(path.is_file(), script)

    def test_every_script_has_help(self):
        for script in ("forge.py", "validate_verdict.py", "make_sxs.py", "make_workbench.py", "blender_mcp_cli.py"):
            with self.subTest(script=script):
                res = run_script(script, "--help")
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertIn("usage:", res.stdout)
        res = run_script("blender_turnaround.py", "--", "--help")
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
