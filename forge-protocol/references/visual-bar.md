# Writing the bar (`art/BAR.md`)

The bar turns the user's goal into criteria that a fresh critic can grade PASS or FAIL from captures alone. The orchestrator writes it from `BRIEF.md` and domain expertise. Research facts and techniques whenever they sharpen a criterion (how real caustics behave, plausible physics constants, type-scale ratios, WCAG contrast). A criterion always states an observable quality; it never describes a picture to match.

## Format

```markdown
# Bar: <title>
BAR-VERSION: v1

## C1 Goal fit
- PASS when: <one observable condition>
- FAIL signs: <what failure looks like>
```

One `## C<id> <name>` heading per criterion, each with a `PASS when:` line (required) and `FAIL signs:`. IDs stay stable across versions; a retired ID is never reused. `forge.py bar publish` manages the version line.

## The shared core

Keep these three in every bar and adapt the wording to the goal:

- **C1 Goal fit**: every must-have in `BRIEF.md` is visibly present and working in at least one capture, cited by still or frame id.
- **C2 Live capture provenance**: every capture comes from the running build named in `MANIFEST.md`, at the size `BRIEF.md` asks for, with no mockups, retouching or mixed builds.
- **C3 State and motion integrity**: no placeholders, missing assets, broken layout, z-fighting, popping or error overlays in any sampled state or frame.

## Goal-specific criteria (C4 onward)

Start from the closest pack in [criteria-packs.md](criteria-packs.md), then make each criterion:

- **Observable**: a critic can point at a region of a still or frame.
- **Binary**: the PASS line has one reading; nothing like "mostly" or "generally".
- **Absolute**: state the quality itself ("shadows darken where objects meet the ground"), never "looks like X" or a comparison with an image.
- **Motivated**: a must-have or the quality target in `BRIEF.md` explains why it exists; cut it otherwise.
- **Checkable in one pass**: use as many criteria as the goal needs. Long bars dilute attention; most land between 4 and 10.

Two extras that suit almost any visual goal:

- **Glance read**: blurred or seen small, each still keeps a clear focal point, value structure and mood (a squint test).
- **Craft at native size**: detail tiles at 100% hold up: crisp edges, no smeared textures, no aliasing on the hero subject.

## Evolving the bar honestly (the ratchet)

The bar may change while the run learns, but only upward unless the user says otherwise.

- **Versions**: `BAR-VERSION` increments on every publish. `forge.py bar publish` snapshots `art/bar-history/BAR-v<N>.md` and appends a `BAR-PUBLISH` event with the type, the reason and the full diff to `artifacts/rounds.log`.
- **Timing**: only between rounds, after the verdict is logged and before the next `CAPTURE`. `forge.py` refuses a publish while a round is open and refuses `CAPTURE` while `BAR.md` has unpublished edits. `validate_verdict.py` rejects a verdict that cites an older version, or when `BAR.md` changed after the round's `CAPTURE`.
- **Allowed freely, always logged**: add a criterion (`--type add`), raise a PASS line (`raise`), clarify wording without changing what passes (`clarify`).
- **Audited**: raising or clarifying a criterion that failed in the last verdict marks the revision `audit=pending`. Before the next capture, a fresh critic with `SCOPE: bar` compares the two versions and returns `BAR-OK` or `BAR-LOWERED`. Clarifications of failing criteria are where quiet loosening hides.
- **User only**: loosening or retiring any criterion (`--type loosen` or `retire`) requires the user's explicit approval, quoted verbatim in `--user-approved`. Never lower the bar to rescue a failing build.
- **Good reasons to revise**: the user clarified the goal; a criterion proved ambiguous; you found a stronger observable target; the build already clears a criterion and a higher one serves the goal better.

Without the scripts, keep the same rules by hand: bump the version line, copy the old file to `art/bar-history/`, and log the reason and a diff.

## Automatic FAIL signs (any domain)

- A must-have that is missing, faked, or only described in text.
- Placeholder content: lorem ipsum, gray boxes, primitive stand-ins for hero objects, default browser controls where the goal calls for craft.
- Missing or broken assets: magenta textures, broken images, unstyled flashes.
- Captures that are not from the live build, or that mix builds.
- Glitches in sampled frames: flicker, z-fighting, popping, layout jumps, console-error overlays.

## Process failures the orchestrator fixes before scoring

- `BAR.md` missing, unparseable, or still holding template placeholders (`forge.py bar publish` refuses these).
- A must-have view or state without a capture, or an incomplete `MANIFEST.md`.
- A verdict with banned phrases, numeric scores, ungraded criteria, uncited stills or invented still ids. `validate_verdict.py` catches these; re-run the critic, never edit its verdict.
