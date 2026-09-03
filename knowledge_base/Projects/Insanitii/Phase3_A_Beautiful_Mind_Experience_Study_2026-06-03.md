# Phase 3: A Beautiful Mind Experience Study

Date: 2026-06-03

## Purpose

This note translates inspiration from Ron Howard's *A Beautiful Mind* into concrete Insanitii gameplay, psychosis-event, audio, HUD, NPC, and post-process design direction.

The key takeaway is not to make every hallucination visually obvious. The film works because it first lets the audience accept distorted reality as ordinary reality, then forces a re-read of earlier scenes. For Insanitii, that means the strongest experience is not constant horror distortion; it is fragile certainty during ordinary life.

## Source Notes

- Britannica summarizes the film as a 2001 biographical drama about John Nash, with parts of the story shown through Nash's delusional perspective. It also notes that the film uses visual hallucinations as a dramatic device even though Nash's real symptoms were reported as mostly auditory and mental. Source: https://www.britannica.com/topic/A-Beautiful-Mind
- PBS's *A Brilliant Madness* describes Nash's delusions being joined by voices and notes that auditory hallucinations are common in schizophrenia. It also frames Nash's recovery around gradual rejection of voices, support, shelter, and the Princeton community treating him as a person rather than only as an illness. Source: https://www.pbs.org/wgbh/americanexperience/films/nash/
- NIMH defines schizophrenia symptoms across psychotic, negative, and cognitive categories. Psychotic symptoms include hallucinations, delusions, and thought disorder; negative symptoms can include difficulty with routine activities such as grocery shopping; cognitive symptoms can affect attention, memory, and decision-making. Source: https://www.nimh.nih.gov/health/publications/schizophrenia
- NAMI frames psychosis as involving hallucinations and/or delusions, including hearing voices, seeing glimpses or distortions, and believing ordinary events or objects have special personal meaning. It emphasizes early, person-centered treatment, coping strategies, and support. Source: https://www.nami.org/types-of-conditions/psychosis/

## Film Mechanisms Worth Stealing

### 1. The hallucination is introduced as normal

Charles, Marcee, and Parcher are staged like normal characters. They are not born from a giant visual glitch. They speak, take up screen time, and occupy the same dramatic grammar as real people.

Insanitii translation:
- Hallucination NPCs should initially render and behave like normal characters.
- Do not always apply a "fake person" shader.
- Telltales should be subtle and testable: no objective-marker confirmation, inconsistent interaction sound, no response from other NPCs, missing reflection, unchanged routine, unusual pathing, or a voice that only the player hears.

### 2. The reveal changes memory, not just the current scene

The film's twist works because the viewer retroactively questions earlier scenes. The moment of diagnosis is not just information; it rewrites the player's confidence.

Insanitii translation:
- Build tasks where earlier instructions become suspect.
- A package route may include a person who gave instructions, but later the HUD objective contradicts them.
- A grocery list may contain one item added by a voice; checking the grounded task list reveals the mismatch.
- A work commute sign may briefly imply a dangerous alternate route, while the objective marker holds steady.

### 3. Pattern-making is both power and vulnerability

Nash's intelligence and pattern hunger are central. The film makes code, numbers, conspiracy, and meaning feel seductive before it becomes dangerous.

Insanitii translation:
- Use false salience as a core psychosis effect.
- Ordinary objects should seem meaningful under high psychosis: receipts, aisle signs, laundry tags, license plates, road markings, package labels, and workplace notes.
- The player should sometimes have to decide whether a pattern is task-relevant or a mental-state distortion.

### 4. Social reality is the main test

The film repeatedly uses other people's reactions as a reality anchor. A person who only Nash can see is exposed because the shared social world does not respond to that person.

Insanitii translation:
- Later NPC systems should include real and hallucinated characters in the same location.
- Real NPCs affect objectives, pathing, audio occlusion, collision, and other NPC reactions.
- Hallucinated NPCs can affect player perception and stress, but should not advance grounded tasks unless the event intentionally corrupts the objective.

### 5. Recovery is gameplay, not an epilogue

The film's emotional center is not just breakdown. It is also coping, support, and learning to live while symptoms remain present.

Insanitii translation:
- Stabilization must be as interactive and satisfying as destabilization.
- Food, medication, breathing, grounding objects, safe rooms, calling a trusted person, sleep, and completing small ordinary tasks should visibly and audibly restore coherence.
- "Winning" a psychosis beat should not require destroying hallucinations. It can mean choosing the grounded objective, reducing distress, and continuing the day.

## Mental-Health Design Guardrails

- Do not make schizophrenia equal to monsters. Chases can exist, but they should be one event type, not the whole condition.
- Include auditory experiences, delusions, cognitive load, negative symptoms, and ordinary-function friction, not only visual hallucinations.
- Keep the protagonist's agency central. The player is not just a victim of effects; they learn tools, supports, and strategies.
- Use respectful labels in docs and UI: "psychosis event", "mental state", "distress", "grounding", "voices", "uncertainty", "stabilization".
- Avoid making medication a magic button or a punishment. It can be one stabilizing tool among several, with thoughtful audio/visual restoration.
- The player should feel that ordinary tasks become difficult because perception, attention, confidence, and social interpretation are strained.

## Post-Process Direction

### Low instability: barely wrong

Goal: The world is functional, but the player feels a small loss of ease.

Effects:
- Slight vignette.
- Slightly shorter depth of field than normal.
- Mild contrast/saturation drift.
- Occasional barely audible whispers.
- HUD objective remains clean.

Implementation state:
- The native post-process controller now supports intensity-driven color/vignette changes and has been extended with camera FOV and depth-of-field controls.

### Mid instability: attention narrows

Goal: Ordinary tasks require more effort.

Effects:
- DOF focal distance shortens toward nearby task surfaces.
- FOV subtly widens, making the world feel less stable.
- Saturation hue leans cooler or sickly in peripheral space.
- World-reactive Tripo/set-dressing anchors pulse and drift with false significance.
- Voices begin commenting on task choices without fully taking over.

Gameplay:
- Grocery aisle labels briefly rearrange.
- Laundry symbols look over-important.
- Package names or addresses flicker between true and false variants.
- Work commute signs briefly imply hostile meanings.

### High instability: reality competes with interpretation

Goal: The player can still function, but confidence is strained.

Effects:
- FOV pulse becomes noticeable.
- DOF focal distance hunts between the objective and hallucinated anchors.
- Color balance pushes into unstable hues.
- Peripheral objects drift, scale, or shimmer.
- Some audio is diegetic; some is internal; the mix makes that hard to separate.

Gameplay:
- A hallucinated NPC may provide an alternate instruction.
- Objective marker remains the primary grounding system, but it can become noisy around the edges.
- Repeated failure to ground pushes toward a psychosis event.

### Psychosis event: certainty breaks

Goal: A discrete event changes how the player has to reason, not just how the scene looks.

Event concepts:
- Unmarked hallucination: a friendly or unfriendly character appears normal and gives instructions that conflict with the grounded objective.
- Pattern flood: ordinary textures, labels, receipts, and signs seem full of coded meaning.
- Social uncertainty: several people occupy a space; only some are real. The player uses HUD objective, audio cues, collision, and other NPC reactions to decide.
- World shift: a familiar station becomes spatially wrong, but a grounding action can bring it back.
- Voice chorus: friendly and unfriendly voices debate the player's current task, with stereo positioning and volume tied to mental-state pressure.

## HUD Objective Marker Direction

The user specifically removed route markers and wants HUD objective guidance instead. This pairs well with the film-inspired design.

Rules:
- The objective marker is the player's main reality anchor.
- At low and mid instability, it should remain trustworthy.
- At high instability, it can visually strain but should not fully lie unless a psychosis event explicitly teaches that rule.
- During grounding, the marker should clean up first, before the whole world becomes stable.
- Hallucination NPCs should not get the same marker language as real objectives.

## Sound Direction

ElevenLabs psychosis and station sounds should support uncertainty instead of just stingers.

Layers:
- Ordinary Foley: fridge hum, grocery scanner, washing machine, folding fabric, package tape, car indicator, office fluorescent buzz.
- Mental-state bed: low room tone that bends with instability.
- Friendly voices: grounding, reassurance, practical reminders, soft warnings.
- Unfriendly voices: suspicion, shame, threat, false urgency, commands that conflict with objectives.
- False salience sounds: tiny click/whisper cues on irrelevant props, suggesting significance.

Rules:
- Friendly and unfriendly voices should be able to coexist.
- Internal voices should sometimes sound like they occupy real space, but grounding should reveal them as internal through mix changes.
- Station Foley should be concrete and believable so hallucination audio has a stable baseline to corrupt.

## Immediate Implementation Backlog

1. Tune the new FOV/DOF post-process controller in PIE at low, mid, high, psychosis, and grounded states.
2. Add a HUD objective marker actor/widget that replaces route markers as the main navigation aid.
3. Create a hallucinated-character event that initially uses normal rendering and only exposes subtle telltales.
4. Add voice-line categories: friendly, unfriendly, false instruction, grounding reminder, and task commentary.
5. Add "pattern flood" material/post-process pass for signs, labels, package tags, receipts, and floor markings.
6. Expand station tasks so hallucinated instructions can conflict with grounded objective state without breaking completion logic.
7. Add objective-marker corruption states: clean, strained, noisy edge, psychosis-event challenged, restored.

## Current VFX Pass Hook

The current native post-process pass already moved in this direction by adding:

- Mental-state-driven camera FOV shift.
- Psychosis FOV pulse.
- Mental-state-driven DOF focal distance.
- Mental-state-driven aperture/F-stop changes.
- Runtime readbacks for current camera FOV and focal distance.

This gives us the foundation for "attention narrows, space feels wrong, then grounding restores focus" instead of relying only on color grading.

## Verification

After the closed-editor build and relaunch, live MCP verification passed:

- `bridge_ping.py`: bridge responded from Unreal Editor on `127.0.0.1:55655`.
- `report_insanitii_layout_positions.py`: wide Day 1 layout remained locked with `max_deviation: 0.0` and no compact-zone hits.
- `report_insanitii_tripo_assets.py`: eight Tripo Smart Mesh actors remained placed and tagged with LOD0 triangle counts from 735 to 2,284.
- `probe_insanitii_postprocess_vfx.py`: `INS_PostProcessController` exposes the new FOV/DOF properties, with `MaxFOVShift` 16.0, `PsychosisFOVPulse` 7.5, `UnstableFocalDistance` 520.0, and debug readback including FOV and Focus.
