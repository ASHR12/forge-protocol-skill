# Writing the bar (`art/BAR.md`)

The bar turns the user's goal into criteria that a fresh critic can grade PASS or FAIL from captures alone. The orchestrator writes it from `BRIEF.md` and domain expertise. Research facts and techniques whenever they sharpen a criterion (how real caustics behave, plausible physics constants, type-scale ratios, WCAG contrast). A criterion always states an observable quality; it never describes a picture to match.

## Format

```markdown
# Bar: <title>
BAR-VERSION: v1

## C1 Goal fit
- PASS when: every item under "Must show" in BRIEF.md is visibly present and working in at least one capture, cited by still or frame id.
- FAIL signs: a must-have is missing, faked, broken, or only described in text.

## C2 Live capture provenance
- PASS when: every still and frame comes from the running build named in MANIFEST.md, at the size BRIEF.md asks for, with no mockups, retouching or mixed builds.
- FAIL signs: static plates, edited screenshots, stills from different builds, wrong size.

## C3 State and motion integrity
- PASS when: every sampled state and walkthrough frame shows finished content with no placeholders, missing assets, broken layout, z-fighting, popping or error overlays.
- FAIL signs: placeholder boxes or text, magenta textures, flicker, console-error overlays, layout breaks mid-interaction.

## C4 <goal-specific name>
- PASS when: <one observable condition>
- FAIL signs: <what failure looks like>
```

One `## C<id> <name>` heading per criterion, each with a `PASS when:` line and a `FAIL signs:` line. IDs stay stable across versions, and a retired ID is never reused.

## The shared core

Keep C1 to C3 in every bar, and adapt their wording to the goal:

- **C1 Goal fit**: every must-have in `BRIEF.md` is visibly present and working in at least one capture.
- **C2 Live capture provenance**: every capture comes from the running build named in `MANIFEST.md`, at the size `BRIEF.md` asks for.
- **C3 State and motion integrity**: nothing unfinished or broken in any sampled state or frame.

## Goal-specific criteria (C4 onward)

Start from the closest pack in [criteria-packs.md](criteria-packs.md), then make each criterion:

- **Observable**: a critic can point at a region of a still or frame.
- **Binary**: the PASS line has one reading; nothing like "mostly" or "generally".
- **Absolute**: state the quality itself ("shadows darken where objects meet the ground"). Never grade against a reference image, screenshot or mockup: no "matches the reference", "looks like the screenshot", "as in the mockup". Technical terms that only share the word are fine: a chart's reference line, a physics reference frame, a reference implementation of an algorithm.
- **Motivated**: a must-have or the quality target in `BRIEF.md` explains why it exists; cut it otherwise.
- **Checkable in one pass**: use as many criteria as the goal needs. Long bars dilute attention; most land between 4 and 10.

Extras that suit almost any visual goal:

- **Glance read**: blurred or seen small, each still keeps a clear focal point, value structure and mood (a squint test).
- **Craft at native size**: detail crops at 100% hold up: crisp edges, no smeared textures, no aliasing on the hero subject.
- **Form without post** (when the build uses post-processing): the no-post still of each hero view keeps its silhouette, material separation and focal point ([criteria-packs.md](criteria-packs.md), 3D pack).

## Evolving the bar honestly (the ratchet)

The bar may change while the run learns, but only upward unless the user says otherwise.

- **Publishing**: every publish bumps `BAR-VERSION`, saves a copy as `art/bar-history/BAR-v<N>.md`, and logs `BAR-PUBLISH` in `artifacts/rounds.log` with the type, the reason and the diff ([project-files.md](project-files.md)).
- **Timing**: only between rounds, after the round's verdict is logged and before the next `CAPTURE`. Never publish while a round is open, and never capture while `BAR.md` differs from its last published copy. A verdict that grades an older version, or a round whose `BAR.md` changed after its `CAPTURE`, does not count: re-run the critic on the current bar.
- **Allowed freely, always logged**: add a criterion (`add`), raise a PASS line (`raise`), clarify wording without changing what passes (`clarify`).
- **Audited**: raising or clarifying a criterion that failed in the last verdict needs a fresh critic with `SCOPE: bar`, comparing the two versions against that verdict, to return `BAR-OK` before the next capture. A `BAR-LOWERED` answer means revert, or get the user's approval for a loosening. Clarifications of failing criteria are where quiet loosening hides.
- **User only**: loosening or retiring a criterion (`loosen`, `retire`) needs the user's explicit approval, quoted verbatim in the log. Never lower the bar to rescue a failing build.
- **Good reasons to revise**: the user clarified the goal; a criterion proved ambiguous; you found a stronger observable target; the build already clears a criterion and a higher one serves the goal better.

## Automatic FAIL signs (any domain)

- A must-have that is missing, faked, or only described in text.
- Placeholder content: lorem ipsum, gray boxes, primitive stand-ins for hero objects, default browser controls where the goal calls for craft.
- Missing or broken assets: magenta textures, broken images, unstyled flashes.
- Captures that are not from the live build, or that mix builds.
- Glitches in sampled frames: flicker, z-fighting, popping, layout jumps, console-error overlays.

## Process failures to fix before grading

- `BAR.md` missing, without a version line, with duplicate ids, or still holding template placeholders.
- A must-have view or state without a capture, or an incomplete `MANIFEST.md`.
- A verdict that fails the verdict check in [critic-prompt.md](critic-prompt.md). Re-run the critic; never edit its verdict.
