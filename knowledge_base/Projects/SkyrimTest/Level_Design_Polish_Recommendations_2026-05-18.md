# SkyrimTest Level Design Polish Recommendations - 2026-05-18

## Project Read

The level design spec, `The Gray Mother's Lair`, frames Gragar's mission as a linear Skyrim-style rescue/revenge level:

1. Wake in a ransacked village.
2. Use Hunter Clairvoyance to investigate and follow the trail.
3. Leave through the village gate and survive a 3-goblin ambush.
4. Reach a shrine midpoint for exposition.
5. Optional Giant's Camp detour for worldbuilding.
6. Enter the Gray Mother's Lair.
7. See Camilla caged and trolls devouring Gragar's mother.
8. Unlock Gragar's Rage, defeat trolls, then fight the Gray Mother.
9. Free Camilla and close on the Rohm vista.

## Highest-Impact Additions

### 1. Hunter Clairvoyance Breadcrumb Pass

Add a visible tracking layer through the whole critical path:

- glowing footprints from the wake-up point
- faint blue/green trail wisps leaving the village
- highlighted broken cart, drag marks, dropped family object, and shrine clue
- short ghostly echo silhouettes at 2-3 key investigation spots

This makes the level's core mechanic visible even if the actual ability is only a presentation prototype.

### 2. Three Cinematic Trigger Moments

Use the existing empty Level Sequences:

- `PlayerWakes`: low camera, fire/smoke/audio sting, first look at destruction, reveal the trail.
- `Ambush`: gate trigger, ambushers move from cover, camera/VO/audio cue redirects attention.
- `GrayMotherEmerges`: after trolls are defeated, ceiling/ledge reveal, boss drops or steps into silhouette.

The sequences should be short and readable, not cutscene-heavy.

### 3. Ambush Readability Upgrade

Stage `Ambusher1`, `Ambusher2`, and `Ambusher3` around the gate with distinct lanes:

- one obvious front attacker
- one flank from broken wall/fence
- one delayed rear/side attacker

Add a trigger volume before the gate and a small combat pocket with cover, room to dodge, and clear exit framing toward the shrine path.

### 4. Shrine Midpoint Story Beat

Make the shrine a clear emotional/compositional pause:

- survivor body or wounded villager marker
- readable altar/sigil
- blood/trail clue pointing toward the lair
- framed view of cave route beyond the shrine

This is the level's breath between ambush and horror reveal.

### 5. Boss Arena Composition Pass

In the lair, create a strong first-read triangle:

- Camilla in cage as one focal point
- Gragar's mother/fire/trolls as the center horror focal point
- Gray Mother's emergence point above or beyond the arena

Use color separation: warm orange fire for the mother/trolls, cold gray/green for the lair, red pulse for Rage.

### 6. Gragar's Rage Presentation

Even if the full combat mechanic is prototype-level, show it clearly:

- red post-process pulse
- sound swell
- temporary weapon glow
- on-screen or diegetic cue that stamina pressure is gone
- rage ends before or during the Gray Mother transition to create pressure

### 7. Outro Vista Framing

After Camilla is released, guide the player to a vista point:

- framed Rohm skyline
- safe quiet space after boss
- Camilla placed beside or slightly ahead of the player
- village/cave behind the player, city ahead

This turns the ending into a level design statement instead of just an endpoint.

## Presentation Checklist

- Add trigger volumes for the three named sequences.
- Add simple objective text or diegetic signs for each beat.
- Add one lighting color script: village ash, mountain cold, shrine calm, lair horror, vista relief.
- Add blocking volumes or visual blockers so the player cannot bypass the intended read order.
- Add ambient audio zones: village wind/fire, mountain trail, shrine hush, cave wet/low rumble, boss sting.
- Add screenshot/camera bookmarks for the same walkthrough shots in the PDF.

## Recommended Next Implementation Pass

Build a lightweight presentation layer first:

1. Clairvoyance trail actors.
2. Gate ambush trigger.
3. Sequence trigger volumes for `PlayerWakes`, `Ambush`, and `GrayMotherEmerges`.
4. Lair reveal staging and Rage VFX placeholder.
5. Post-boss Camilla release/vista marker.

This will make the existing level read as a polished level design walkthrough even before final art, animation, and combat tuning.
