# Unity input, UI and audio: Input System, rebinding, UI Toolkit and uGUI, menus, HUDs, the mixer and Web audio

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the player controls or hears the build: input actions and rebinding, menus, pause and settings, HUDs and world-space labels, music, effects and spatial sound. Camera input is in [camera-and-animation.md](camera-and-animation.md); jump buffering, hit-stop and feedback timing are in [characters-physics-and-feel.md](characters-physics-and-feel.md); capturing overlay UI is in [validation.md](validation.md).

## Contents

- The Input System and the legacy trap
- Actions, control schemes and PlayerInput
- Rebinding and saved bindings
- UI input and the EventSystem
- UI Toolkit or uGUI
- Text, fonts and TextMesh Pro
- Menus, pause and settings
- HUDs and world-space UI
- Audio Mixer, groups and snapshots
- Spatial sound and variation
- Music loops and Web audio
- Symptom → cause

## The Input System and the legacy trap

**Goal.** Every input goes through the Input System, the only handler new 6.6 projects turn on, and no old input call survives.

**Build.**
1. Check Edit > Project Settings > Player > Other Settings > Active Input Handling. The 6000.6.4f1 templates ship it set to the Input System package alone; keep it that way. Use Both only to run legacy third-party code during a migration.
2. Never call `UnityEngine.Input` (`Input.GetAxis`, `Input.GetKey`, `Input.mousePosition`): with only the Input System active, the first call throws.
3. Confirm the package version in `Packages/packages-lock.json` (1.20.0 on this editor).
4. Old mouse callbacks keep working: since 6.4, `OnMouseDown`, `OnMouseDrag` and `OnMouseUp` fire under the Input System.
5. When code must compile both ways, guard it with the `ENABLE_INPUT_SYSTEM` and `ENABLE_LEGACY_INPUT_MANAGER` defines.

**Watch for.** Tutorials, older Asset Store packages and Starter Assets versions call `Input.GetAxis`. Changing Active Input Handling can prompt an Editor restart; treat it as a step for a person ([setup.md](setup.md)).

**Critic checks.** PASS when the console and player logs captured with each round show no input-handling exceptions. FAIL signs: the legacy-input exception in a log; a control that works in the Editor but not in the build.

**API facts** (check the installed version):
- Reading `UnityEngine.Input` while only the Input System is active throws "You are trying to read Input using the UnityEngine.Input class, but you have switched active Input handling to Input System package in Player Settings." (verified on 6000.6).
- The project templates bundled with 6000.6.4f1 set Active Input Handling to the Input System package only (verified on 6000.6).
- Since 6.4, MonoBehaviours receive `OnMouseDown`, `OnMouseDrag` and `OnMouseUp` with the Input System (verified on 6000.6).

## Actions, control schemes and PlayerInput

**Goal.** Every control is a named action that works alike on keyboard and mouse and on a gamepad, and each one produces a response the player sees right away.

**Choose.**
- **Project-wide actions** by default: one actions asset assigned in Project Settings > Input System Package, reached from code through `InputSystem.actions`, preloaded at startup and enabled by default.
- **A PlayerInput component** when a player needs device pairing, control-scheme switching or actions wired to methods without code; it is the base of local multiplayer.
- **Direct action references** (fields that point at actions, or a C# class generated from the asset) for code-first single-player games.

**Build.**
1. Lay out two action maps: Player (Move, Look, Jump, Attack, Interact, Sprint, Pause) and UI (Navigate, Submit, Cancel, Point, Click, Scroll). The default project-wide actions already hold most of these.
2. Make one control scheme per device family (Keyboard&Mouse, Gamepad), with WASD as a 2D composite, stick dead zones as processors, and Hold or Tap as interactions.
3. Read actions in `Update` (`ReadValue`, `WasPressedThisFrame`, or the performed and canceled callbacks), buffer presses, and apply physics intent in `FixedUpdate`.
4. Scale stick look by delta time but not mouse look, since a mouse delta already covers the frame.
5. Switch to the UI map when a menu opens and back on close, and keep Background Behavior on a reset option, so keys don't stay held after the window loses focus.

**Watch for.** Actions from an asset other than the project-wide one stay disabled until enabled. Two PlayerInput components in a single-player game can split the devices between them.

**Critic checks.** PASS when, for each control scheme the brief names, the frames recorded just after a scripted press show its result within a frame or two. FAIL signs: no response on the gamepad; look speed that changes with frame rate; a character still walking after focus returns.

**API facts** (check the installed version):
- Project-wide actions are reached through `InputSystem.actions`, are preloaded when the app starts, and are enabled by default (verified on 6000.6).
- PlayerInput notifies by Send Messages, Broadcast Messages, Invoke Unity Events or Invoke CSharp Events (verified on 6000.6).
- `InputAction` offers `IsPressed`, `WasPressedThisFrame` and `WasReleasedThisFrame` (verified on 6000.6).
- Background Behavior is Reset And Disable Non Background Devices, Reset And Disable All Devices, or Ignore Focus (verified on 6000.6).

## Rebinding and saved bindings

**Goal.** Players can remap any action, see the current binding in plain words, and keep their choices across launches.

**Build.**
1. Disable the action (or its map), then start `PerformInteractiveRebinding` on it, excluding the mouse for key rebinds and canceling through Escape; re-enable the action when the operation completes or cancels.
2. Dispose of the rebinding operation when it ends.
3. Show each binding with `GetBindingDisplayString`, refreshed after every change, and offer a reset that calls `RemoveAllBindingOverrides`.
4. Save the overrides with `SaveBindingOverridesAsJson` and restore them at startup with `LoadBindingOverridesFromJson`, before the first input is read.
5. Learn the layout from the package's "Rebinding UI" sample; write the game's own screen.

**Watch for.** A binding that two actions share fails quietly; check for conflicts after each rebind.

**Critic checks.** PASS when the settings screen shows every action's current binding in readable form, and a capture after a scripted rebind and restart shows the new binding. FAIL signs: raw control paths on screen; bindings reset after a restart.

**API facts** (check the installed version):
- Rebinding an enabled action throws "Cannot rebind action ... while it is enabled" (verified on 6000.6).
- `PerformInteractiveRebinding` returns a rebinding operation that must be disposed, or it leaks unmanaged memory (verified on 6000.6).
- `SaveBindingOverridesAsJson` and `LoadBindingOverridesFromJson` store and restore binding overrides as JSON (verified on 6000.6).

## UI input and the EventSystem

**Goal.** Clicks, taps and gamepad navigation always reach the UI, and gameplay doesn't react to clicks meant for a menu.

**Build.**
1. uGUI: keep exactly one EventSystem, with the Input System UI Input Module, never the Standalone Input Module.
2. UI Toolkit panels handle input themselves in 6.6 and don't need the module; if a scene mixes both systems, they share the one EventSystem.
3. When a menu opens, select its first control so gamepad navigation starts somewhere, and keep navigation order sensible.
4. Block gameplay input while the pointer is over UI, and while any menu is open.

**Watch for.** A scene copied from an older project often brings a Standalone Input Module, which leaves clicks dead. A second EventSystem in an additively loaded scene causes warnings and erratic focus.

**Critic checks.** PASS when gamepad-driven menu captures show a visible focus highlight on the selected control, and walkthrough frames after a scripted click show the state change. FAIL signs: no highlight anywhere; a menu that only works with a mouse; a shot fired by clicking a button.

**API facts** (check the installed version):
- uGUI needs the Input System UI Input Module (`InputSystemUIInputModule`); UI Toolkit needs it only before Unity 2023.2 (verified on 6000.6).
- Settings on a scene's UI Input Module take priority over the UI settings in the project-wide actions (verified on 6000.6).

## UI Toolkit or uGUI

**Goal.** Each screen uses the UI system that suits it, built the 6.6 way, and scales cleanly from the smallest to the largest capture size.

**Choose.**
- **uGUI** (Canvas, RectTransform, TextMesh Pro), Unity 6.6's runtime recommendation: in-scene authoring, Inspector events, Animation and Timeline integration, world-space canvases, and the new Safe Area component.
- **UI Toolkit** (UXML, USS and C#), the listed alternative: flex layout, style sheets, transitions, data binding and textureless elements, with backdrop blur and drop shadows new in 6.6. Its UXML and USS are text files an agent can write and diff, which suits menus, settings and HUDs.
- One system per screen; mix them only across screens.

**Build.**
1. UI Toolkit: create a Panel Settings asset (Scale Mode set to Scale With Screen Size, with a reference resolution), and add a Panel Renderer with the UXML and Panel Settings. Register a UI reload callback to find elements, and keep the version check so reloads don't duplicate them.
2. uGUI: set the Canvas Scaler to Scale With Screen Size with a reference resolution, anchor elements to edges and corners, and add Safe Area where screens have notches.
3. Lay out for the smallest capture width the brief names first, then check the largest.

**Watch for.** Tutorials that add a UI Document: in 6.6 the component can't be added to new GameObjects, and the Panel Renderer replaces it; existing UI Documents still run. A UI Document clears its content when disabled, while a Panel Renderer keeps it. Backdrop filters draw only on Screen Space Overlay panels.

**Critic checks.** PASS when every UI screen keeps its layout, margins and type hierarchy at each captured size, with nothing clipped or overlapping. FAIL signs: text cut off at a small width; elements drifting off center at a large one; UI under a notch or rounded corner.

**API facts** (check the installed version):
- The UI Document component is obsolete in 6.6 and can't be added to new GameObjects in the Editor; the Panel Renderer replaces it, and existing UI Documents keep working (verified on 6000.6).
- `PanelRenderer.RegisterUIReloadCallback` hands the root visual element and a version number to the callback on each reload (verified on 6000.6).
- Unity 6.6 recommends uGUI for runtime UI and lists UI Toolkit as the alternative (verified on 6000.6).
- uGUI 2.6, shipped with 6000.6, adds a Safe Area component that insets a RectTransform to the device's safe area (verified on 6000.6).

## Text, fonts and TextMesh Pro

**Goal.** Every line of text is sharp and readable in the captures, set in the typefaces the design calls for, with no missing characters.

**Build.**
1. uGUI text is TextMesh Pro, which lives inside uGUI; import its Essential Resources once with Window > TextMeshPro > Import TMP Essential Resources, or run that menu item from an editor script.
2. Never add the old `com.unity.textmeshpro` package; it is a deprecated stub.
3. Ship every font the game uses, including fallbacks for other scripts and weights; the Web build can't reach the user's installed fonts. Record each font's license ([assets-and-import.md](assets-and-import.md)).
4. Build signed-distance-field font assets for headings that scale, and dynamic font assets with fallbacks for player-entered or translated text.
5. Set sizes from the capture resolution in `BRIEF.md`, with body text contrast of at least 4.5:1 ([../criteria-packs.md](../criteria-packs.md), web-ui).

**Watch for.** A project without the Essential Resources shows text objects with no default font; check for the TextMesh Pro folder under Assets before the first capture.

**Critic checks.** PASS when all text is crisp and readable at capture size, with a clear type hierarchy and no glyph boxes. FAIL signs: blurry or aliased text; tiny labels on a large capture; squares where characters should be.

**API facts** (check the installed version):
- TextMesh Pro merged into uGUI in its 2.0.0 release, and `com.unity.textmeshpro` 5.0.0 is a deprecated stub on 6000.6 (verified on 6000.6).
- Unity Web can't use fonts installed on the user's machine, so every font must be in the project (verified on 6000.6).

## Menus, pause and settings

**Goal.** Every screen of the game is a finished, distinct state: title, play, pause, settings and results, reachable by keyboard, mouse and gamepad.

**Build.**
1. Treat screens as states that own their UI and input map. Pause asks the single time-scale owner for zero ([characters-physics-and-feel.md](characters-physics-and-feel.md)), switches to the UI map, and moves audio to a paused mix.
2. Animate menus on unscaled time, so they move while the game is paused.
3. Settings: master, music and effects volume; look sensitivity and invert Y; shake and flash strength; the quality tier; window size and fullscreen on the Mac; rebinding. Save them and apply them at startup.
4. Make every screen work with all three input routes, and offer a quit or restart that returns cleanly.

**Watch for.** At a time scale of zero, menu animations on scaled time freeze, and so do coroutines that wait in scaled seconds.

**Critic checks.** PASS when every captured state looks finished and distinct, and paused frames show no motion behind the menu. FAIL signs: a placeholder menu; two screens drawn over each other; gameplay still moving under the pause menu; settings that reset on relaunch.

## HUDs and world-space UI

**Goal.** The HUD is legible at capture size and never covers the focal subject; world labels sit with their objects and hide when something blocks them.

**Build.**
1. Keep HUD elements on edges and corners, inside safe areas, with one hierarchy of importance, sized from the capture resolution.
2. Keep the HUD out of tonemapping and bloom: draw it as a Screen Space - Overlay canvas or an overlay panel rather than inside the 3D scene, and confirm in a capture with bloom on that the text stays crisp. Overlay UI is missing from a camera-only capture, so capture it with the screen route ([validation.md](validation.md)).
3. World-space UI: a world-space uGUI canvas, or a Panel Renderer in world space with its world-space size set. Face the camera, scale with distance, and hide or fade labels when geometry blocks them.
4. Pool health bars and damage numbers, and cap how many show at once.

**Watch for.** A Canvas Scaler left at Constant Pixel Size makes the HUD tiny in a large capture. A world-space canvas processes UI events through its Event Camera, so set it to the camera the player sees through.

**Critic checks.** PASS when HUD text reads cleanly at the captured resolution, world labels stay next to what they name and disappear behind obstacles, and the main subject is never covered. FAIL signs: soft or glowing UI text; labels visible through solid walls; panels covering the main subject.

**API facts** (check the installed version):
- The Panel Renderer carries `worldSpaceSize` and `worldSpaceSizeMode` for UI Toolkit panels placed in the world (verified on 6000.6).
- Canvas Scaler modes include Constant Pixel Size and Scale With Screen Size, the latter scaling from a Reference Resolution (verified on 6000.6).

## Audio Mixer, groups and snapshots

**Goal.** Sound is mixed in groups the player controls, moods and pause change the mix smoothly, and audio can be checked even though captures are silent.

**Build.**
1. Make one Audio Mixer with Master above Music, Effects, UI, Ambience and Voice, and route every Audio Source's output to a group.
2. Expose the player's volume controls as parameters (right-click a group's volume, Expose to script) on groups that no snapshot changes, because `SetFloat` takes a parameter away from snapshots. Convert slider values to decibels, and apply saved volumes in `Start`, not `Awake` or `OnEnable`.
3. Build snapshots for the game's moods (Gameplay, Paused, Underwater), and move between them with `TransitionTo` over a short time.
4. Duck music under voice and key sounds, and keep UI and pause-menu sounds playing through a pause with `ignoreListenerPause` while `AudioListener.pause` holds the rest.
5. Write every sound trigger and snapshot change to the log with a timestamp; captures are silent, so the log (or the user's own listening) is the audio evidence.

**Watch for.** On the Web, the mixer applies group volume only; effects such as a low-pass in the pause snapshot don't play there (see Music loops and Web audio).

**Critic checks.** PASS when the round's log shows the expected sound triggers and snapshot changes at the right moments, and a settings capture shows working volume controls. FAIL signs: events with no logged sound; a pause with no mix change; volume settings that don't persist.

**API facts** (check the installed version):
- After `AudioMixer.SetFloat` sets an exposed parameter, snapshots no longer control it; it returns false when the name isn't exposed, and Unity warns against calling it in `Awake`, `OnEnable` or after-scene-load initialization (verified on 6000.6).
- `AudioMixerSnapshot.TransitionTo` interpolates to the snapshot over the time given (verified on 6000.6).
- `AudioListener.pause` pauses every Audio Source, and `ignoreListenerPause`, set only from script, lets chosen sources keep playing (verified on 6000.6).

## Spatial sound and variation

**Goal.** Sounds sit in space at the scene's scale, and repeated sounds never play identically twice in a row.

**Build.**
1. Put one Audio Listener on the camera, or deliberately on the player in third person.
2. World sounds use a Spatial Blend of 1 (full 3D), Min and Max Distance set to the scene's scale, and logarithmic rolloff, or a custom curve where gameplay clarity matters; music and UI stay 2D (Spatial Blend 0).
3. Vary repeats with an Audio Random Container: several clips, Random or Shuffle playback, Avoid Repeating Last, and small volume and pitch ranges; play it through an Audio Source. Its automatic trigger (Pulse or Offset) suits footsteps, rain and automatic fire.
4. Trigger footsteps from animation events, with the clip set chosen by the ground's material.
5. Delay sounds from distant events by distance at the speed of sound, about 343 m/s, timed on the game clock or an Awaitable, never a `System.Threading` timer, which never fires on the Web ([foundation.md](foundation.md), Async code).

**Watch for.** An Audio Source's pitch is ignored when it plays a Random Container; set pitch ranges on the container. A huge Min Distance removes all falloff.

**Critic checks.** PASS when the log shows repeated events picking varied clips and distant events triggering later, and the user's listening check, when the brief asks for one, confirms the space. FAIL signs: one clip for every footstep; a distant explosion heard on the flash frame.

**API facts** (check the installed version):
- The Audio Random Container plays playlists in Sequential, Shuffle or Random order, with Avoid Repeating Last, volume and pitch randomization, and Manual or Automatic (Pulse, Offset) triggers through `AudioSource.Play` (verified on 6000.6).
- `AudioSource.spatialBlend` runs from 0 (fully 2D) to 1 (fully 3D) (verified on 6000.6).
- `AudioSource.pitch` is ignored when the source plays an Audio Random Container (verified on 6000.6).
- 6.6 imports second- and third-order ambisonic clips, but decoding them needs a third-party or custom decoder plug-in (verified on 6000.6).

## Music loops and Web audio

**Goal.** Music loops without a click on every target, and Web audio starts on the player's first interaction.

**Build.**
1. Load types: Streaming for long music on the Mac, Decompress On Load for short effects; on the Web, Compressed In Memory for music and Decompress On Load for effects.
2. Loop cleanly: cut loops at zero crossings, and for an intro followed by a loop, schedule the loop with `PlayScheduled` on the audio clock.
3. For Web builds, author music as WAV with at least 1,024 samples of silence at the start, and put the loop start after that silence, because the Web's AAC encoding can alter the first 1,024 samples and click at the loop point.
4. Gate audio behind a first click, tap or key press: the browser blocks playback until then, so show a start screen and begin music on that input.
5. Keep Web audio simple: the mixer changes only group volume, pitch must stay positive, and mixer effects don't run.

**Watch for.** Music that starts in the Editor and never in the browser is the interaction gate. On iPhones in silent mode, Web clips set to Decompress On Load don't play, while Compressed In Memory ones do.

**Critic checks.** PASS when the Web build's first capture shows a start prompt, and the log shows music starting right after the first input. FAIL signs: a Web build with no prompt and no music; a log of music starting before any input.

**API facts** (check the installed version):
- Browsers block audio until the user clicks, touches or presses a key on the page (verified on 6000.6).
- On the Web, the Audio Mixer supports groups and their volume through `SetFloat` only, with no other properties or effects (verified on 6000.6).
- Web builds encode clips as AAC, whose first 1,024 samples can change; a WAV source with leading silence and a later loop point avoids the glitch (verified on 6000.6).
- Clips load as Decompress On Load, Compressed In Memory or Streaming; the Web supports only the first two (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| The first input call throws | legacy `UnityEngine.Input` with only the Input System active | the call site, and Active Input Handling |
| Controls dead in the build only | an actions asset that isn't project-wide and was never enabled | where the actions are enabled |
| Keys stay held after switching windows | Background Behavior set to Ignore Focus | the Input System settings |
| Rebinding throws | the action is enabled during the rebind | disabling the action before the rebind |
| Rebinds lost after restart | overrides not saved, or loaded after first use | the save and load calls and their timing |
| Clicks do nothing | a Standalone Input Module, or no EventSystem | the EventSystem's input module |
| A gamepad can't reach the menu | nothing selected when the menu opens | the first selected control |
| "Add UI Document" isn't possible | the 6.6 change to the Panel Renderer | a Panel Renderer with Panel Settings |
| Text shows no font | TMP Essential Resources not imported | the TextMesh Pro folder in Assets |
| Squares instead of characters on the Web | fonts or fallbacks not in the project | the font assets and fallback list |
| HUD tiny at a large capture | Canvas Scaler at Constant Pixel Size | the scaler mode and reference resolution |
| HUD missing from captures | camera-only capture route | the capture route ([validation.md](validation.md)) |
| Pause snapshot stops working | `SetFloat` on a parameter the snapshot controls | which parameters are exposed and where |
| Footsteps sound identical | one clip, or pitch set on the Audio Source | the Random Container's clips and ranges |
| No sound on the Web | playback started before a user interaction | the start screen and the first-input handler |
| A click at the music loop point on the Web | AAC changing the first samples | the WAV's leading silence and loop point |
