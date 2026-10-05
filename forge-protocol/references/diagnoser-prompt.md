# Stuck-loop Diagnoser and escalation ladder

Repeating the same punch list to the same builder burns budget without moving the result. When a loop stalls, a fresh Diagnoser finds the structural bottleneck and steers the builders up the escalation ladder. It never grades and never touches the bar; only a fresh critic, or the user when they grade, can return WIN.

## Triggers

Run the Diagnoser when any of these holds. Check the first three from `artifacts/rounds.log` and the saved verdicts after every round:

- The same criterion has failed for the mode's diagnose count of consecutive rounds since the last steer (defaults: 2 in Sprint, 3 in Standard and Forge).
- Two or more `RECAPTURE` verdicts in a row for the same round.
- The build id did not change between two rounds, meaning the punch round changed nothing in the product.
- A builder reports a technique or stack ceiling.

## Orchestrator steps

1. Pause punch rounds and log `DIAGNOSE-HOLD`.
2. Spawn a fresh Diagnoser, separate from the builders and the critic, with the prompt below and file paths only. On Three.js builds, include the paths to `references/threejs/validation.md` and to the topic files `PLAN.md` names for the failing pieces.
3. Dispatch the builders with `artifacts/diagnosis/R<n>-steer.md` as their primary brief and the latest punch list as a secondary input. Log `DIAGNOSE-STEER` and, when the steer climbs a rung, `ESCALATE` with the rung number.
4. Return to the normal round loop. Streak counting restarts after the steer.

## Escalation ladder

Climb from cheap, global levers to structural ones, and skip rungs when the evidence points higher. The Diagnoser picks the rung; [criteria-packs.md](criteria-packs.md) lists concrete levers per domain.

1. **Presentation**: light, exposure, color and post (3D; post only once the no-post still passes); type scale, spacing and color tokens (UI); scales and labels (data viz).
2. **Surface craft**: materials and shaders; component styling and imagery; mark styling and annotation.
3. **Structure and content**: authored geometry and density; layout and component rebuilds; encodings and data shaping.
4. **Pipeline**: render passes, simulation method or animation system; the rendering approach itself (DOM to canvas or WebGL).
5. **Stack**: change engine or framework (Canvas to Three.js to Unity, for example). Agree a stack change with the user when it alters the approved plan.

If the top useful rung is exhausted and the criterion still fails, stop and report best-so-far honestly instead of looping.

## Prompt

~~~markdown
You are the stuck-loop Diagnoser for a forge-protocol build. The builders and the critic have failed the
same criteria across several rounds. You do not edit code, you do not grade, and you never soften or
lower art/BAR.md. Inspect the evidence, find the root bottleneck, and write a steer brief to
artifacts/diagnosis/R<n>-steer.md.

Inputs (open them yourself): BRIEF.md, art/BAR.md, the last three verdicts in artifacts/verdicts/,
artifacts/rounds.log, the current stills and frames, round comparisons in artifacts/compare/ if any, the
builders' short handbacks, and the source files or generation steps behind the failing criteria. On
Three.js builds, also read threejs/validation.md and the topic files PLAN.md names for the failing
pieces, at the paths you are given.

Write exactly these five sections:
1. Root cause: why the last rounds did not move the failing criteria. Examples: tuning shader constants
   while the geometry is a primitive; post-processing standing in for missing form or material; tuning
   around a core step never checked on a known input (a transform, a simulation, a color conversion);
   ornament piled on a weak base form; color, roughness and normals driven by unrelated noise instead
   of shared causes; stacked camera smoothing that stalls mid-transition; camera framing that hides the
   subject; a type scale with no grid; a physics step too coarse for the stated model.
2. Evidence: the stills, frames, verdict lines and code locations that prove it.
3. Stop doing: the dead-end tactics the builders must drop.
4. Steer for the next one or two rounds: numbered structural actions, naming the escalation rung (1 to 5)
   and the files, assets or passes to rebuild.
5. Success check: what must visibly change in the next captures, per failing criterion.
~~~
