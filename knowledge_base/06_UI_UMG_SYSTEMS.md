# UI / UMG Systems — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. UMG Overview

**Unreal Motion Graphics (UMG)** is UE5's UI framework. All HUDs, menus, and dialogue boxes are built with Widget Blueprints (`WBP_` prefix).

### Widget Blueprint vs HUD
- **Widget Blueprint** — modern system; use for all UI (recommended)
- **HUD class** — legacy; still functional but WBP preferred

---

## 2. Widget Blueprint Structure

### Designer Tab (Visual Layout)
- Drag-and-drop widget components from the Palette
- Set anchors, alignment, and size in the Details panel
- Anchoring is CRITICAL for multi-resolution support

### Graph Tab (Event Graph)
- Standard Blueprint graph
- Events: `Event Construct`, `Event Tick`, `Event Destruct`
- Contains widget-specific variables and binding logic

---

## 3. Core Widget Types

### Layout Containers
| Widget | Purpose |
|--------|---------|
| `Canvas Panel` | Free-form positioning (drag anywhere); good for HUD |
| `Vertical Box` | Stack children top-to-bottom |
| `Horizontal Box` | Stack children left-to-right |
| `Grid Panel` | Grid layout |
| `Wrap Box` | Wraps content to next row |
| `Scroll Box` | Scrollable container |
| `Overlay` | Stacks children on top of each other |
| `Size Box` | Forces a specific size on its child |
| `Scale Box` | Scales child to fill available space |
| `Border` | Container with background and border |

### Display Widgets
| Widget | Purpose |
|--------|---------|
| `Text` | Static or dynamic text display |
| `Image` | Image or material |
| `Progress Bar` | Fill bar (health, XP, timer) |
| `Spacer` | Empty space for layout |
| `Rich Text Block` | Text with inline styling |

### Interactive Widgets
| Widget | Purpose |
|--------|---------|
| `Button` | Clickable; fires `OnClicked`, `OnHovered`, `OnUnhovered`, `OnPressed`, `OnReleased` |
| `Check Box` | Toggle on/off |
| `Slider` | Draggable float value (0–1) |
| `Editable Text Box` | User text input |
| `Spin Box` | Numeric input with +/- |
| `Combo Box (String)` | Dropdown selector |
| `List View` | Efficiently renders large lists |

---

## 4. Anchoring (Critical for Multi-Resolution)

Anchors define where a widget's position is relative to its parent container.

### Anchor Presets
- **Top-Left**: Fixed distance from top-left corner
- **Top-Center**: Fixed distance from top edge, centered horizontally
- **Center-Center**: Always centered on screen
- **Bottom-Right**: Fixed distance from bottom-right
- **Full Screen Stretch**: Stretches to fill the container

### Best Practices
- **HUD elements**: Anchor to the closest corner/edge they belong near
- **Crosshairs**: Center-Center anchor
- **Health bar**: Bottom-Left anchor
- **Quest tracker**: Top-Right anchor
- **Dialogue box**: Bottom-Center with stretch horizontal

---

## 5. Creating and Adding Widgets to Screen

### Pattern: PlayerController BeginPlay
```
Event BeginPlay →
  Create Widget (Class: WBP_HUD)
  → Return Value → Store in HUDRef (variable of type WBP_HUD)
  → Add to Viewport
  → Set Input Mode Game Only (optionally show/hide mouse cursor)
```

### Show / Hide a Widget
```
Get HUDRef → Set Visibility (Visibility: Hidden/Visible/Collapsed)
OR
Get HUDRef → Remove from Parent  ← destroys the widget instance
```

### Re-create after Remove from Parent
```
Create Widget → Add to Viewport (must create new instance)
```

---

## 6. Variable Bindings

**Automatic per-frame binding: The widget reads a value every frame automatically.**

### Creating a Binding (on a Progress Bar Percent pin)
1. Click the `Percent` property → `Bind` button
2. Creates a new Function Graph
3. In the function: Get PlayerRef → Cast → Get Health / MaxHealth → Divide → Return float

### Binding Example: Health Bar
```
Function: Get HealthPercent
  → Get PlayerController (index 0)
  → Cast To BP_DantooinePlayerController
  → Get PlayerCharRef
  → Get CurrentHealth / Get MaxHealth
  → Return float (0.0–1.0)
```

### When to Use Bindings vs Event Dispatchers

| Method | Pros | Cons |
|--------|------|------|
| **Binding** | Simple, automatic | Called every frame even when not needed |
| **Event Dispatcher** | Only updates when value changes | More setup required |
| **Recommendation** | Use for slow-changing values (health, score) | Use dispatcher for burst updates (score pop) |

---

## 7. Communicating Between Widgets and Game

### Widget → Game (Widget calls game code)
```
In WBP_DialogueBox:
  Button OnClicked (DialogueChoice_1)
  → Get Game Mode → Cast To BP_DantooineGameMode
  → Call AdvanceDialogue (ChoiceIndex: 0)
```

### Game → Widget (Game updates widget)
```
Option A: Direct Reference
  PlayerController has HUDRef (WBP_HUD) → call UpdateHealth(NewHealth)

Option B: Event Dispatcher
  Character broadcasts OnHealthChanged(NewHealth)
  Widget binds to it in Event Construct:
    Get Owning Player → Get Pawn → Cast To Character
    → Bind Event to OnHealthChanged → [CustomEvent: UpdateHealthBar]

  UpdateHealthBar(NewHealth: float):
    Get HealthBar (widget ref) → Set Percent (NewHealth / MaxHealth)
```

---

## 8. WBP Animations (Motion in UI)

### Creating a Widget Animation
1. In Designer tab → Animations section → + New Animation
2. Name it (e.g., `FadeIn`, `SlideInFromBottom`, `PulseQuestBadge`)
3. Add tracks for widgets you want to animate
4. Set keyframes for properties (Render Opacity, Translation, Scale, Color)

### Playing Widget Animations in Graph
```
Play Animation (Animation: FadeIn, Num Loops: 1, Play Mode: Forward)
Reverse Animation (Animation: FadeIn) ← plays backward for FadeOut
Stop Animation (Animation: FadeIn)
Get Animation Time Remaining (Animation: FadeIn) ← returns float
Is Animation Playing (Animation: FadeIn) ← returns bool
```

---

## 9. Input Modes

| Mode | Game Receives | UI Receives | Mouse Cursor |
|------|--------------|-------------|-------------|
| `Set Input Mode Game Only` | ✅ | ❌ | Hidden |
| `Set Input Mode UI Only` | ❌ | ✅ | Visible |
| `Set Input Mode Game and UI` | ✅ | ✅ | Configurable |

### Pattern: Dialogue Box Opens
```
[Player presses Interact on NPC]
  → Set Input Mode Game and UI
  → Show Mouse Cursor (true)
  → Create WBP_DialogueBox → Add to Viewport

[Player selects dialogue choice]
  → Remove WBP_DialogueBox from Parent
  → Set Input Mode Game Only
  → Show Mouse Cursor (false)
```

---

## 10. Common Widget Patterns

### HUD Pattern (WBP_HUD)
```
Canvas Panel:
  ├── Health Bar (Progress Bar, bottom-left anchor)
  │     Binding: Get Health / MaxHealth
  ├── Quest Tracker (Vertical Box, top-right anchor)
  │     Text: Current objective text
  └── Interact Prompt (Text, bottom-center anchor)
        Visibility: Hidden by default; shown when near interactable

Event Construct:
  → Get Owning Player Pawn → Cast → Store PlayerRef
  → Bind to dispatcher: OnObjectiveChanged → UpdateQuestText
```

### Dialogue Box Pattern (WBP_DialogueBox)
```
Canvas Panel:
  └── Border (semi-transparent background)
        ├── NPC Name (Text)
        ├── Dialogue Text (Text, multiline)
        └── Choices Box (Vertical Box)
              ├── Button[0] (Choice text)
              ├── Button[1] (Choice text)
              └── Button[2] (Choice text)

PopulateDialogue(DialogueNode: ST_DialogueNode):
  Set NPC Name text
  Set Dialogue Text
  For Each Choice in DialogueNode.Choices:
    Create Choice Button Widget → Add to Choices Box → Bind OnClicked

OnChoiceClicked(ChoiceIndex: int):
  Get Game Mode → Advance Dialogue (ChoiceIndex)
```

### Quest Tracker Pattern (WBP_QuestTracker)
```
Contains: 
  QuestTitle: Text
  ObjectiveList: Scroll Box of Text entries
  CompletedCount: Text

UpdateObjectives(Objectives: Array of String):
  Clear Scroll Box
  For Each Objective:
    Create Text Widget → Set Text → Add to Scroll Box
```

### Level Complete Screen (WBP_LevelComplete)
```
Canvas Panel:
  ├── Level Complete Title (Text, centered)
  ├── Score Panel (Horizontal Box with stats)
  ├── Continue Button → OnClicked → Load Next Level
  └── Main Menu Button → OnClicked → Open Level (MainMenu)

Event Construct:
  → Play FadeIn animation
  → Set Score text from Game Instance data
```

---

## 11. Dantooine Widget Reference

| Widget | Parent | Purpose |
|--------|--------|---------|
| `WBP_HUD` | UserWidget | Main game HUD: health, quest tracker, interact prompt |
| `WBP_DialogueBox` | UserWidget | NPC dialogue with choice buttons |
| `WBP_QuestTracker` | UserWidget | Sub-widget inside HUD showing quest objectives |
| `WBP_InteractPrompt` | UserWidget | "Press E to Interact" prompt near interactables |
| `WBP_SparringHUD` | UserWidget | Combat overlay: timer, hits taken, opponent health |
| `WBP_LevelComplete` | UserWidget | End of level screen with results and continue button |

### HUD Creation Pattern (In BP_DantooinePlayerController)
```
Event BeginPlay:
  Create Widget (WBP_HUD) → Store HUDRef → Add to Viewport
  Set Input Mode Game Only
```

### Interact Prompt Show/Hide (From Player Character)
```
Event ActorBeginOverlap (Trigger):
  Cast to BPI_Interactable implementer →
  PlayerControllerRef → Get HUDRef → Cast To WBP_HUD →
  Show InteractPrompt (InteractionText: "Press E to Use Workbench")

Event ActorEndOverlap:
  PlayerControllerRef → Get HUDRef → Cast To WBP_HUD →
  Hide InteractPrompt
```
