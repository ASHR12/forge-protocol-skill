# Bar: {{TITLE}}
BAR-VERSION: v0

Derived from BRIEF.md. The critic grades every criterion PASS or FAIL on the current captures, with cited
evidence. Publish revisions only between rounds with `forge.py bar publish`: raising and clarifying are
fine, loosening or retiring needs the user's explicit approval. Guide: references/visual-bar.md.

## C1 Goal fit
- PASS when: every item under "Must show" in BRIEF.md is visibly present and working in at least one capture, cited by still or frame id.
- FAIL signs: a must-have is missing, faked, broken, or only described in text.

## C2 Live capture provenance
- PASS when: every still and frame comes from the running build named in MANIFEST.md, at the size BRIEF.md asks for, with no mockups, retouching or mixed builds.
- FAIL signs: static plates, edited screenshots, stills from different builds, wrong size.

## C3 State and motion integrity
- PASS when: every sampled state and walkthrough frame shows finished content with no placeholders, missing assets, broken layout, z-fighting, popping or error overlays.
- FAIL signs: placeholder boxes or text, magenta textures, flicker, console-error overlays, layout breaks mid-interaction.

<!-- Add goal-specific criteria from C4 on. Start from references/criteria-packs.md, rewrite each one so a
     critic can observe it in this project's captures, and delete this comment and the example below. -->

## C4 <name>
- PASS when: <observable condition>
- FAIL signs: <what failure looks like>
