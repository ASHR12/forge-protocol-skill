# Project files

A run lives in plain files, so any agent or a fresh session can pick it up. Create them by hand or with any tool you like. The names below are defaults: if the project already has conventions, adapt them and note the mapping in `BRIEF.md`.

## Layout

```text
BRIEF.md                     goal, must-haves, quality target, captures, budgets, policies
PLAN.md                      Standard and Forge: tools, pieces, risks
art/
  BAR.md                     the current bar (format in visual-bar.md)
  bar-history/BAR-v<N>.md    a copy of every published version
  LEDGER.md                  Forge, and any run that uses third-party assets
artifacts/
  rounds.log                 one line per event
  stills/                    still-NN images and MANIFEST.md for the current round
  walkthrough-frames/        frame-NN images when there is motion
  history/R<nn>/             a copy of each round's stills and manifest
  verdicts/                  R<nn>.md, plus gate, plan and bar verdicts
  diagnosis/                 R<n>-steer.md from the Diagnoser
  turnarounds/               hero-asset turnaround strips and their stats
  compare/                   optional round comparisons; blind-pair keys go in compare/keys/
  progress.html              optional progress page
```

Sprint needs only `BRIEF.md`, `art/BAR.md`, `artifacts/rounds.log`, `stills/`, `history/` and `verdicts/`. Create the other folders when a step first needs them.

## BRIEF.md

```markdown
# <title>: brief
Mode: <sprint | standard | forge> · Created: <date> · Publish: LOCKED

## Goal
<one sentence: what the user wants to exist and why>

## Must show
1. <what the viewer must see or be able to do; C1 Goal fit grades this list>

## Quality target
<the tier to beat, in plain words: "a launch-day product page", "a moody island scene a studio would post">

## Non-goals
- <what this build deliberately skips>

## Captures
- Size: <for example 1920x1080 desktop and 390x844 phone>
- Views and states: <one still per must-have view or state>
- Motion: <walkthrough frames across which moves, or none>

## Budgets
Rounds: <n> · Time: <minutes> · Check-ins: <cadence> · Diagnose after: <n> straight fails of one criterion

## Stack
<stack, and the criteria packs the bar starts from>
<Three.js builds: the pinned revision (for example r186), the renderer, the target backend and its fallback, quality tiers and what each keeps, and target devices with any frame budget>

## Policies
- Publish stays LOCKED until the user explicitly unlocks it.
- Third-party assets only under a license that allows this use, each recorded in the ledger.
- Model or vendor names the product must show: <none, or the exact names and why>
```

You decide the captures and may change them between rounds; C2 checks the captures against this section.

## PLAN.md (Standard and Forge)

```markdown
# <title>: plan
Mode: <mode> · Stack: <stack>

## Tools (probed live)
| Tool | Status (found, missing, fallback) | Role | How it was verified |

## Pieces
| Piece | Builder brief | How it is judged (turnaround, gate check, round critic) |

## Risks and fallbacks
- <risk>: <fallback>
```

## LEDGER.md

One row per visible element. Nothing ships as `placeholder`.

```markdown
| Element | Type | Source (authored, procedural, downloaded) | License | Status (placeholder, draft, final) |
```

## rounds.log

One event per line, newest last. Indented lines below an event continue it (used for bar diffs).

```text
<ISO time> | stage=<plan|setup|build|gate|loop|handoff> | round=<R<n>|n/a> | role=<orchestrator|builder|critic|diagnoser|user> | result=<EVENT> | build=<id|n/a> | bar=<v<N>|n/a> | session=<id|n/a> | note=<short text>
```

- Events: `INIT`, `PLAN`, `APPROVED`, `BUILD`, `GATE-PASS`, `GATE-FAIL`, `SMOOTHING`, `BAR-PUBLISH`, `BAR-OK`, `BAR-LOWERED`, `CAPTURE`, `RECAPTURE`, `FAIL`, `WIN`, `WIN-VOIDED`, `BLOCKED`, `DIAGNOSE-HOLD`, `DIAGNOSE-STEER`, `ESCALATE`, `CHECK-IN`, `BUDGET-EXHAUSTED`, `BUDGET-EXTENDED`, `PUBLISH-UNLOCK`, `STOP`, `HANDOFF`.
- A round opens with `CAPTURE` and closes with `FAIL`, `WIN`, `RECAPTURE` or `BLOCKED`. A RECAPTURE keeps the same round number for the next capture.
- Extra `key=value` fields may follow `session`, for example `critic=fresh-session` when no subagent mechanism exists.
- `BAR-PUBLISH` adds `type=<initial|add|raise|clarify|loosen|retire>`, the reason in `note`, `approved="<the user's words>"` for loosen and retire, and the diff as indented lines. `ESCALATE` adds `rung=<n>`. `BUDGET-EXTENDED` adds what was extended, for example `rounds=+5`.
- `session` is the environment's identifier for the subagent, if it exposes one. Write `n/a` otherwise; never invent one. Never log keys, tokens or credential-bearing URLs.

## MANIFEST.md

Written next to the stills on every capture. Every row carries the same build id.

```markdown
| still | build | size | view | captured |
| --- | --- | --- | --- | --- |
| still-01.png | 3f9c2e1 | 1920x1080 | hero | 2026-10-05T12:00:00Z |
```

On Three.js builds, add one provenance line above the table, read from the running page, such as `three.js r186 · backend webgpu (compat off) · adapter <vendor, architecture> (hardware) · browser <name, version> (headed) · DPR 1 · canvas 1920x1080 · tier high`. Name variants in the view column (`hero`, `hero no-post`, `hero near`), including any still taken at another tier or debug mode.

## Builder handback

Builders reply with facts only: no verdict words, no quality claims.

```text
R<n> handback
build: <id>
captures: artifacts/stills/ (<count>), artifacts/walkthrough-frames/ (<count>)
addressed: <punch item numbers>
not addressed: <numbers, each with the reason and any proposed escalation rung>
```
