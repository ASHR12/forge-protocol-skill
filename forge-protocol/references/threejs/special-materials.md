# Three.js special materials: optical and physical models

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this only when the goal features a material whose look comes from a specific optical or physical effect. Ordinary PBR surfaces, weathering and relief are in [materials.md](materials.md).

## Contents

- Choosing the optical model
- Glass and clear bodies
- Gems and faceted crystals
- Thin films and iridescence
- Diffraction and holographic foil
- Cloth and fabric
- Hair and fur
- Skin, wax, leaves and other translucent organics
- Soft bodies and jelly
- Granular and deformable ground
- Lava and emissive flows
- Brushed and anisotropic metal
- Symptom → cause

## Choosing the optical model

**Goal.** Name what defines the look, then pick the model that produces it. Ruling out the wrong model saves more time than tuning the right one.

**Choose.**

| The look is defined by | Model | Section |
| --- | --- | --- |
| a bent, tinted view through a solid | transmission along a path, with absorption | Glass |
| sparkle and colored fire from a cut stone | rays bouncing inside a closed body, with dispersion | Gems |
| swirling rainbow bands on a thin layer | thin-film interference | Thin films |
| spectral streaks that slide as the light moves | diffraction from fine grooves | Foil |
| a soft glow on fibers at grazing angles | sheen over a woven structure | Cloth |
| strands with highlights along their length | fiber shading on cards, shells or strands | Hair and fur |
| light glowing through thin parts | subsurface scattering or translucency | Translucent organics |
| a body that wobbles, then settles | one soft-body state feeding shape and optics | Jelly |
| tracks pressed into a surface | a deformable heightfield | Granular ground |
| heat glowing through cracks in a dark crust | emission from a temperature field | Lava |
| highlights stretched by a grain | anisotropic reflection | Brushed metal |

**Watch for.** Common wrong choices: a soap bubble rendered as a glass sphere, foil painted with a rainbow texture, fur as a noisy texture on a smooth shell, lava as an orange emissive map.

## Glass and clear bodies

**Goal.** Glass reads as light traveling through a volume: the scene behind bends, thick parts tint deeper than thin edges, rims brighten at grazing angles, and what shows through matches what surrounds the object.

**Choose.**
- Built-in physical transmission for most glass (bottles, windows, lenses, product shells): one refraction at the front surface, absorption over a set thickness, roughness blur, optional dispersion.
- An image-space two-surface path for thick, curved hero bodies whose exit surface matters (cast glass, crystal sculpture, ice). Render the body's far surfaces to a buffer first, then refract each pixel toward its exit point. It copes with open or overlapping shells but cannot see exits outside the frame.
- A ray path against the mesh's own triangles for closed faceted gems (next section).

**Build.**
1. Use one HDR environment for the background, the reflections and the light passing through; a mismatch makes the object look cut from another scene.
2. Set the index of refraction from the real material: about 1.33 for water and about 1.5 for common glass.
3. Choose absorption as the tint that a known thickness should show, then make thickness vary, through a thickness map or the true path length on a custom path.
4. Let roughness frost the view through the glass, and let exposure handle bright refracted highlights instead of clamping HDR early.

**Watch for.** Opacity used instead of transmission, which gives a gray ghost rather than glass; tint colors converted to linear twice, which darkens them silently; transparent objects that vanish behind the glass.

**Critic checks.** PASS when thick parts are tinted deeper than thin edges, rims are brighter than the face-on center, the background seen through the glass is bent but continuous with its surroundings, and no opaque black areas appear. FAIL signs: one flat tint everywhere, glass that reads as gray plastic, a view through the glass that doesn't belong to the scene, black patches.

**Diagnose.** The interior lags while orbiting → the far-surface buffer comes from the previous frame; render it every frame, before the main pass, with the same camera.

**API facts** (check the installed version):
- `transmission` refracts a capture of the opaque scene, so ordinary transparent objects behind the glass don't show through it; keep `opacity` at 1 (verified on r186).
- Built-in absorption follows `attenuationColor` at `attenuationDistance` (default Infinity, meaning no tint) over a path of `thickness` times the object's scale. The mesh's real depth is never measured, so encode variation in `thicknessMap` (verified on r186).
- `ior` is documented for 1.0 to 2.333 (default 1.5), and `dispersion` (default 0) acts only on transmissive materials (verified on r186).

## Gems and faceted crystals

**Goal.** Sparkle comes from light bouncing inside a closed, precisely cut body and leaving through facets at angles that change with every small turn; colored fire comes from dispersion splitting the light as it exits.

**Build.**
1. Model a watertight cut with real proportions (table, crown, girdle, pavilion). The cut is what makes the image.
2. Refract the view ray in, trace it against the gem's own triangles through an acceleration structure, keep it inside while total internal reflection holds, and stop after a bounded number of bounces.
3. Exit with a slightly different index per color channel, or per wavelength sample, to make fire.
4. Sample the environment at an explicit mip level, and light the gem with small bright sources against a darker surround so the facets flash.

**Watch for.** Gem indices above the built-in range need the custom path. Too few bounces leave the pavilion dark. Dispersion faked as a screen-space color shift reads as a cheap rainbow.

**Critic checks.** PASS when bright flashes sit on individual facets and change between captured views, colored fire appears near facet edges, and the pavilion stays bright. FAIL signs: an even rainbow sheen, a dark or gray interior, sparkle that ignores the viewing angle.

## Thin films and iridescence

**Goal.** Film colors come from interference, so they depend on the film's thickness and the viewing angle: they flow as the film drains and shift as you move. A soap bubble is a film in air, not a glass ball.

**Choose.**
- Built-in iridescence for a coating over a base material: beetle shells, coated lenses, oil on dark asphalt, anodized metal.
- A custom air-film-air model for free-floating bubbles: no base, mostly transparent, color only in the reflected light.

**Build.** Drive thickness from a field: thinner at the top as the film drains, thicker at the bottom, swirled by slow flow. Draw a bubble's back membrane before its front. If the shape wobbles, take normals from the deformed shape.

**Critic checks.** PASS when bubbles stay mostly clear, with faint color bands that swirl, shift between views and reflect the surroundings, and coated surfaces change hue with angle. FAIL signs: a rainbow painted evenly over the surface, opaque or strongly refracting bubbles, bands that never move.

**API facts** (check the installed version):
- `iridescence` takes its film thickness from `iridescenceThicknessRange` (default 100 to 400 nm), and the green channel of `iridescenceThicknessMap` picks a value within it (verified on r186).
- A transparent `DoubleSide` material is drawn back faces first, then front faces; `forceSinglePass` turns that off (verified on r186).

## Diffraction and holographic foil

**Goal.** Foil color is computed from wavelength, groove direction and spacing, and the light and view directions, so the colors move whenever either direction moves. Nothing is painted.

**Build.** Define grooves in the object's own frame, with masks choosing direction, spacing and depth per region. For each light and view direction, find which wavelengths the grooves reinforce, convert that spectrum to RGB, and add it as HDR light over a printed base. Long light sources draw long streaks; small ones draw points.

**Critic checks.** PASS when spectral streaks slide across the foil as the object or light turns between captures, plain areas stay plain, and the pattern turns with the object. FAIL signs: a static rainbow texture, colors stuck to the screen, an even rainbow over the whole surface.

## Cloth and fabric

**Goal.** Fabric reads through its drape (weight, fold size, how it hangs) and its surface (weave scale and a soft response at grazing angles).

**Choose.** A modeled or pre-simulated drape for still shots, baked animation for repeatable motion, and live simulation only when interaction is the point, with collisions against the bodies it touches.

**Build.**
- Derive all weave maps (color, normal, roughness, occlusion) from one shared yarn pattern, at a scale that matches real thread counts, and keep macro folds in the mesh.
- Pick the response by fabric: strong sheen for velvet and fleece, little for cotton and linen, anisotropy for satin and silk.
- Finish hems and seams, since edges are where cloth shows its thickness.

**Watch for.** Unrelated noise in each map makes cloth look printed. Soft stretch constraints make it rubbery. Folds pass through themselves or the body.

**Critic checks.** PASS when folds hang with weight, the fabric shows the response its type implies (a soft grazing glow on velvet, a dry matte cotton), the weave holds up in the closest view, and cloth never clips through bodies. FAIL signs: stiff plastic folds, rubbery stretching, a visible tile grid, intersections.

**API facts** (check the installed version):
- `sheen` scales `sheenColor`, which defaults to black, so raising `sheen` alone changes nothing; `sheenRoughness` defaults to 1 (verified on r186).

## Hair and fur

**Goal.** Hair reads as fibers: a soft, broken silhouette, highlights running along the strands, darker roots and brighter tips, and shadows cast by the fibers themselves.

**Choose.** Cards (textured strips) for game characters and long hair at mid distance; shells (stacked offset layers with a strand mask) for short dense fur and carpets; strands (instanced GPU ribbons) for hero close-ups and interaction, switching to shells or cards with distance.

**Build.**
- Groom first: flow direction over the surface, length by region, clumping.
- Shade along the fiber: a bright primary highlight and a tinted secondary one, darker roots, tips that glow when backlit.
- Keep strands rooted and unable to stretch, with wind and contact bending them from the root.
- Make the shadow pass use the same deformed fibers.

**Watch for.** Shell layers visible at the silhouette, card edges and sorting artifacts, one plastic highlight, roots floating off the skin, strands that stretch, and motion that changes with frame rate.

**Critic checks.** PASS when the silhouette is soft and broken into fibers, highlights follow the hair flow, roots are darker than tips, and fur shadows show fibrous structure. FAIL signs: visible layers or card edges, a helmet-like sheen, hair passing through hands or ground.

**API facts** (check the installed version):
- `alphaToCoverage` smooths alpha-tested card edges but works only with MSAA (`antialias: true`); `alphaHash` avoids sorting at the cost of grain that temporal antialiasing cleans up (verified on r186).
- On node materials the shadow pass reuses `positionNode` (or `castShadowPositionNode` when set) and honors `maskShadowNode`; with patched shaders on the WebGL renderer, give the mesh a matching `customDepthMaterial` (verified on r186).

## Skin, wax, leaves and other translucent organics

**Goal.** Light enters these materials and leaves a little way off, so terminators soften and thin parts glow when lit from behind.

**Choose.** A built-in translucency material where the renderer has one; wrapped diffuse with a warm tint for cheap skin; a baked thickness map for backlit glow in ears, fingers, leaf blades and candles; rough transmission for wax and jade.

**Build.** Keep albedo less saturated than it looks, because scattering adds color. Vary roughness by region (an oily nose, matte cheeks). Bake thickness so thin regions brighten when backlit. Make leaves two-sided, with a yellow-green tint in the light passing through.

**Critic checks.** PASS when ears, fingers or leaf blades glow warm when backlit, and skin terminators are soft with a slight red transition. FAIL signs: hard black terminators on faces, leaves dark from behind, an orange glow over everything.

**API facts** (check the installed version):
- `MeshSSSNodeMaterial` (WebGPU, marked experimental) adds a translucency term driven by `thicknessColorNode` and related thickness nodes; the WebGL renderer has the `SubsurfaceScatteringShader` add-on instead (verified on r186).

## Soft bodies and jelly

**Goal.** One simulated state drives the shape, the refraction and the shadow. The body keeps its volume, wobbles, and comes to rest.

**Build.**
1. Simulate a coarse volumetric cage with a fixed time step and volume preservation, then drive a smooth render shell from it.
2. Recompute the shell's normals after each step, and feed that same shell to refraction, absorption and shadows.
3. Damp internal and whole-body motion at rates that don't depend on frame rate, let the body sleep at rest, and reset it if any value turns non-finite.

**Critic checks.** PASS when, across walkthrough frames after a poke or a drop, the body squashes, wobbles a few times and returns to its rest shape, with its refraction and shadow deforming along with it. FAIL signs: endless jiggle, collapse, refraction of the undeformed shape, sinking through the floor.

## Granular and deformable ground

**Goal.** Sand, snow and mud remember contact: tracks sink in, push material into raised rims, persist, and relax the way the material would.

**Build.**
- Keep a heightfield over the active area, as a window that moves with the player in large worlds. On contact, lower the surface and move the displaced amount into the rim, so material is conserved.
- Over time, relax slopes steeper than the material can hold: sand slumps, snow keeps steeper walls, mud keeps its shape.
- Change shading where the surface was disturbed (wet sand darker, fresh snow brighter, churned mud glossier), with normals taken from the heightfield, and filter grain sparkle by pixel footprint so it stays fine and stable.
- Throw particles from impacts, and run deformation, particles and shading from one clock.

**Critic checks.** PASS when tracks are sunk with raised rims, persist across frames and soften where the material would, and grain highlights stay fine and stable in motion. FAIL signs: flat decals with no depth, glittering noise, tracks that vanish between frames.

**API facts** (check the installed version):
- `displacementMap` moves vertices along their normals by its red channel and leaves the normals unchanged, so pair it with matching normals on a mesh dense enough to carry the detail (verified on r186).
- `StorageTexture` works only on the WebGPU renderer's WebGPU backend, not its WebGL fallback: compute passes write it and materials sample it, which suits a deformable heightfield (verified on r186).

## Lava and emissive flows

**Goal.** One temperature field explains everything: the color, the glow, a dark cooling crust, the motion, and the light the flow throws on its surroundings.

**Build.** Map temperature to color along a hot-body ramp (dark red, orange, yellow-white), with emission rising steeply as it heats. Form crust where it cools (dark, rough, cracked) and let the cracks show the heat beneath. Move it with a flow field that shears and folds rather than sliding as one sheet. Add heat shimmer and embers above the hottest parts, light the surroundings with real lights, and rank its brightness against the other emitters in HDR.

**Critic checks.** PASS when brightness gathers in cracks and channels while the crust is dark and rough, nearby rock picks up warm light, and the flow still reads in the no-post still. FAIL signs: flat orange everywhere, an even glow, structure that exists only in the bloom.

## Brushed and anisotropic metal

**Goal.** Brushing stretches highlights across the brush lines: straight brushing gives straight streaks, and spun or turned parts give radial ones.

**Build.** Point the anisotropy direction across the grain (a direction map for circular grain), align the fine streak texture with the grain, and keep tangents consistent across the part.

**Critic checks.** PASS when highlights stretch in the one direction the grain sets, radially on spun parts. FAIL signs: round highlights on brushed metal, streaks running the wrong way, a direction flip across a seam.

**API facts** (check the installed version):
- `anisotropy` raises roughness only along its direction (the tangent turned by `anisotropyRotation`, or the red-green vector of `anisotropyMap`), so highlights stretch along that direction (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Glass looks like gray plastic | opacity used instead of transmission, or no environment to refract | `transmission` and `opacity` on the material, and `scene.environment` |
| Black patches in glass | missing far-surface data, the wrong face side, or exits outside the frame | the far-surface buffer shown alone |
| Glass tint is the same everywhere | a flat color multiply, or constant thickness with no map | `attenuationColor`, `attenuationDistance` and the thickness map |
| Glass shows a different world from its surroundings | refraction and background use different environments | the environment each one reads |
| The glass interior lags while orbiting | far-surface buffer rendered in an earlier frame | when the far-surface pass runs within the frame |
| A gem looks dark inside | too few bounces, or an index the built-in path can't reach | the bounce cap, and `ior` against its documented range |
| A rainbow looks painted | color from UVs or a texture instead of thickness, wavelength or grooves | what drives the color: thickness, wavelength or a texture |
| Foil pattern slides as the object turns | grooves defined in world or camera space | the coordinate space of the groove masks |
| A bubble looks like a glass ball | modeled as a refracting solid instead of a thin film | the material model: a film in air, or transmission |
| Cloth looks printed | weave maps from unrelated noise | whether every weave map comes from one yarn pattern |
| Raising sheen does nothing | `sheenColor` still black | `sheenColor` on the material |
| Fur shows layers or card edges | too few shells, no edge coverage, card sorting | a silhouette crop at a grazing angle |
| Hair shadows look solid | shadow pass using undeformed or simplified geometry | the shadow alone, and what the shadow pass reads |
| Skin looks waxy or dead | too much scattering or none; one roughness everywhere | a roughness view, and the face lit from behind |
| Jelly keeps jiggling or gains energy at rest | shape and volume constraints solved separately, or damping on only part of the motion | the body's motion over frames after a poke |
| Tracks look like stickers | decals without a heightfield, or displacement without normals | a grazing view across a track |
| Lava is flat orange | emission not driven by temperature; no crust | the temperature field shown alone |
