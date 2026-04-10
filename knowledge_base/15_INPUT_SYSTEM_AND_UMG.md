# Enhanced Input System and UMG Widget Blueprints
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Game Development with UE5 Vol.1 (Tiow Wee Tan)
> Covers the Enhanced Input system (UE5 default), Widget Blueprint creation, HUD design, and all UMG patterns.

---

## 1. ENHANCED INPUT SYSTEM (UE5)

### Why Enhanced Input?
- Replaces the legacy Input Action Mappings
- Context-based: same button can do different things in different contexts
- Supports modifiers (dead zones, swizzle, negate), composites, and chorded actions
- Required in UE5.1+ for new projects

### Core Assets
| Asset | Prefix | Purpose |
|-------|--------|---------|
| Input Action | `IA_` | Defines WHAT can happen (Move, Jump, Attack) |
| Input Mapping Context | `IMC_` | Maps input devices to actions with context |

### Dantooine Input Assets
```
IA_Move     — Move the player (axis 2D)
IA_Look     — Camera look (axis 2D)
IA_Jump     — Jump button (digital)
IA_Interact — Interact with world objects (digital)
IA_Attack   — Lightsaber attack (digital)
IA_Block    — Lightsaber block (hold)
IMC_Dantooine — Maps keyboard/gamepad to all above actions
```

### Input Action Types
| Type | Output Values | Use |
|------|--------------|-----|
| `Digital (bool)` | true / false | Buttons: Jump, Fire, Interact |
| `Axis 1D (float)` | -1.0 to 1.0 | Throttle, zoom |
| `Axis 2D (Vector2D)` | X/Y each -1 to 1 | Move, Look |
| `Axis 3D (Vector)` | X/Y/Z each -1 to 1 | VR 6DOF input |

### Creating Input Assets via exec_python
```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()

# Input Action
ia = at.create_asset("IA_Move", "/Game/Dantooine/Data/Input", unreal.InputAction, unreal.InputAction_Factory())

# Input Mapping Context
imc = at.create_asset("IMC_Dantooine", "/Game/Dantooine/Data/Input", unreal.InputMappingContext, unreal.InputMappingContext_Factory())
```

### Wiring Enhanced Input in PlayerController
```
Event BeginPlay (PlayerController)
  → Get Local Player Subsystem → Add Mapping Context (IMC_Dantooine, Priority: 0)

Event BeginPlay (Character)
  → Enable Input (PlayerController reference)
```

### Binding Input Actions in Blueprint
```
Input Action IA_Move (Triggered)
  → Action Value (Vector2D)
  → Add Movement Input
    → World Direction: Get Actor Forward Vector (for X) / Get Actor Right Vector (for Y)
    → Scale Value: Action Value X / Y

Input Action IA_Jump (Started)
  → Jump

Input Action IA_Look (Triggered)
  → Add Yaw Input (Action Value X)
  → Add Pitch Input (Action Value Y × -1) [invert Y for natural camera]
```

### Input Modifiers
Add to Individual Mappings in IMC:
- `Swizzle Input Axis Values` — swaps X/Y axes (controller sticks)
- `Negate` — flips value direction
- `Dead Zone` — ignores small analog values (0.0 to 0.25 range)
- `Scale` — multiplies value by a factor
- `Smooth` — interpolates between frames for smoother feel

---

## 2. UMG WIDGET BLUEPRINT SYSTEM

### Widget Blueprint vs. Actor
- Widget Blueprints = the UI (2D screen elements)
- They do NOT exist as world actors
- They are created, displayed, and removed programmatically

### Widget Hierarchy
```
WidgetBlueprint (WBP_HUD)
└── Canvas Panel (root container)
    ├── Horizontal Box (layout)
    │   ├── Image (health icon)
    │   └── Progress Bar (health bar)
    ├── Text Block (quest objective)
    └── Vertical Box
        ├── Text Block (score label)
        └── Text Block (score value)
```

### Common Widget Types
| Widget | Use |
|--------|-----|
| `Canvas Panel` | Free-position root container |
| `Horizontal Box` | Left-to-right layout |
| `Vertical Box` | Top-to-bottom layout |
| `Overlay` | Stack widgets on top of each other |
| `Grid Panel` | Grid-based layout |
| `Size Box` | Force a specific size on its child |
| `Scale Box` | Scale child to fill available space |
| `Scroll Box` | Scrollable list |
| `Text Block` | Display text; can bind to variable |
| `Rich Text Block` | Text with inline formatting |
| `Image` | Display a texture or material |
| `Button` | Clickable; has OnClicked event |
| `Progress Bar` | Fill bar (0.0–1.0); can bind |
| `Slider` | Draggable input (0.0–1.0) |
| `Check Box` | Boolean toggle |
| `Editable Text` | User text input |
| `List View` | Dynamic list with item entries |
| `Tile View` | Grid of item tiles |
| `Border` | Container with background/padding |
| `NamedSlot` | Placeholder in parent widget for child content |

---

## 3. CREATING WIDGETS IN BLUEPRINTS

### Create and Display HUD
```
Event BeginPlay (PlayerController)
  → Create Widget
    → Class: WBP_HUD
    → Owning Player: Self
  → [Store reference in variable "HUDWidget"]
  → Add to Viewport
    → Widget: HUDWidget
    → Z Order: 0 (higher = in front)
```

### Remove from Screen
```
HUDWidget → Remove from Parent
```

### Show/Hide Without Removing
```
HUDWidget → Set Visibility
  → InVisibility: Visible / Collapsed / Hidden
```

### Widget Z Order (layering)
| Z Order | Use |
|---------|-----|
| 0 | Game HUD elements |
| 1 | Dialogue overlay |
| 2 | Inventory/menus |
| 9 | Pause screen |
| 100 | Loading screens |

---

## 4. WIDGET VARIABLE BINDINGS

**Bindings automatically update UI every tick when the bound function runs.**

### Creating a Binding
1. Select a Progress Bar in the Widget Designer
2. In Details → Percent → click dropdown → Create Binding
3. Implement the function:
```
Get Player Character → Cast To BP_PlayerJediCharacter → Get Health → Divide by MaxHealth → Return (Float 0–1)
```

### Alternative: Event-Driven Updates (Recommended for Performance)
Instead of tick-based bindings, update the widget only when values change:

```
In BP_PlayerJediCharacter:
  Event Dispatcher: OnHealthChanged (Float NewHealth, Float MaxHealth)
  
  TakeDamage:
    Calculate new health
    Broadcast OnHealthChanged (NewHealth, MaxHealth)

In WBP_HUD:
  Event BeginPlay:
    Get Player Character → Cast → Bind OnHealthChanged → HandleHealthChanged
  
  HandleHealthChanged (Float NewHealth, Float MaxHealth):
    HealthBar Progress Bar → Set Percent (NewHealth / MaxHealth)
    HealthText → Set Text (Format Text "{0}/{1}")
```

---

## 5. WIDGET ANIMATION

### Creating Animations
1. In Widget Designer → click Animations tab (bottom left)
2. "+" to create new animation → name it (e.g., "FadeIn")
3. Select widget element → click "+ Track" → choose property (Color, Opacity, Translation)
4. Set keyframes using the timeline

### Playing Animations
```
Play Animation
  → Animation: FadeIn (reference from My Animations panel)
  → Start At Time: 0.0
  → Num Loops to Play: 1
  → Play Mode: Forward / Reverse / Ping Pong

Play Animation in Reverse
Stop Animation
Is Animation Playing → Bool
```

### Common Animation Use Cases
- `FadeIn` / `FadeOut` — widget opacity from 0 to 1
- `SlideIn` — translate widget from off-screen
- `PulseBeat` — health icon scales briefly on damage
- `QuestComplete` — quest tracker animates into view

---

## 6. WIDGET COMMUNICATION PATTERNS

### Widget → Game World
```
Widget (Button Clicked)
  → Get Player Character (world access)
  → Cast → Call function
```

### Game World → Widget (Recommended: Event Dispatcher)
```
Character broadcasts OnQuestComplete
  → WBP_QuestTracker receives via binding
  → Widget updates its own display
```

### Widget → Widget (via Parent)
```
WBP_HUD
  └── WBP_HealthBar (child widget component)
  └── WBP_QuestTracker (child widget component)

HUD gets reference to child widgets during its BeginPlay via Get Child Widget
```

---

## 7. INPUT MODES

### Input Mode: Game Only (during gameplay)
```
Set Input Mode Game Only
  → Player Controller: Self (or GetPlayerController)
```
- Mouse is hidden and captured
- Widget interactions are disabled
- Keyboard/gamepad input goes to game

### Input Mode: UI Only (menus, dialogue)
```
Set Input Mode UI Only
  → Player Controller: Self
  → Widget To Focus: WBP_PauseMenu reference
```
- Mouse is visible and free
- All input goes to UI, not game

### Input Mode: Game and UI (HUD visible while playing)
```
Set Input Mode Game and UI
  → Player Controller: Self
  → Widget To Focus: (optional)
  → Hide Cursor During Capture: true
```
- Mouse is captured during gameplay
- UI can still receive events (button clicks etc.)

### Cursor Visibility
```
Set Show Mouse Cursor → true / false
```

---

## 8. DIALOGUE BOX SYSTEM (PATTERN)

### WBP_DialogueBox Structure
```
Canvas Panel
└── Border (dialogue background)
    └── Vertical Box
        ├── Text Block (SpeakerName)
        ├── Rich Text Block (DialogueText)
        └── Vertical Box (ChoicesPanel)
            ├── [WBP_DialogueChoice slot 1]
            ├── [WBP_DialogueChoice slot 2]
            └── [WBP_DialogueChoice slot 3]
```

### Show Dialogue Line
```
Function: ShowDialogueLine (ST_DialogueLine Line)
  → SpeakerNameText → Set Text (Line.SpeakerName)
  → DialogueText → Set Text (Line.LineText)
  → Clear Choices Panel children
  → For Each Choice in Node.Choices:
      → Create WBP_DialogueChoice widget
      → Set choice text
      → Bind OnChoiceSelected event
      → Add to ChoicesPanel
```

### Advance Dialogue
```
OnChoiceSelected (Int NextNodeID)
  → Load dialogue node for NextNodeID
  → If -1: Close dialogue box
  → Else: ShowDialogueLine (next node's first line)
```

---

## 9. QUEST TRACKER WIDGET (PATTERN)

### WBP_QuestTracker Structure
```
Canvas Panel
└── Vertical Box
    ├── Text Block "OBJECTIVES"
    └── For each active objective:
        └── Horizontal Box
            ├── Image (checkbox icon)
            └── Text Block (objective description)
```

### Binding Objectives
```
Event BeginPlay:
  Get Game Instance → Cast → Bind OnQuestStageChanged

OnQuestStageChanged (E_QuestStage NewStage):
  → Switch on Enum (NewStage)
    → CollectCrystals: Set objective text to "Collect Force Crystals"
    → BuildLightsaber: Set objective text to "Build your lightsaber"
    → etc.
```

---

## 10. SPARRING HUD (PATTERN)

### WBP_SparringHUD Structure
```
Canvas Panel
├── Left side (Player):
│   ├── Text Block "PLAYER"
│   └── Progress Bar (player health)
├── Center:
│   └── Text Block "VS"
└── Right side (Opponent):
    ├── Text Block "OPPONENT"
    └── Progress Bar (opponent health)
```

---

## 11. HUD ANCHORING AND POSITIONING

### Anchor Presets
- (0,0) = Top-Left
- (0.5,0) = Top-Center
- (1,0) = Top-Right
- (0,0.5) = Mid-Left
- (0.5,0.5) = Center
- (0,1) = Bottom-Left
- (0.5,1) = Bottom-Center
- (1,1) = Bottom-Right

### Safe Zone
For console/mobile:
```
Add → Safe Zone widget → wrap your HUD content inside it
```
This automatically accounts for screen notches and TV overscan.

---

## 12. WIDGET NAMING CONVENTIONS

```
WBP_HUD              — Main gameplay heads-up display
WBP_DialogueBox      — Dialogue conversation window
WBP_QuestTracker     — Active quest/objective tracker
WBP_InteractPrompt   — "Press E to Interact" floating prompt
WBP_SparringHUD      — Health bars during sparring
WBP_LevelComplete    — Victory/completion screen
WBP_PauseMenu        — Pause menu (if implemented)
WBP_MainMenu         — Main menu (if implemented)
WBP_LoadingScreen    — Loading transition
WBP_InventoryItem    — Single item cell in inventory
```

---

## 13. CREATING WIDGET BLUEPRINTS VIA exec_python

```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()

# Create a Widget Blueprint
factory = unreal.WidgetBlueprintFactory()
widget = at.create_asset("WBP_HUD", "/Game/Dantooine/Widgets", unreal.WidgetBlueprint, factory)
print("Created:", widget.get_path_name() if widget else "FAILED")
```

---

## 14. COMMON WIDGET PITFALLS

| Problem | Cause | Fix |
|---------|-------|-----|
| Widget appears but is invisible | Visibility set to Hidden/Collapsed | Set Visibility to Visible |
| Widget overlaps entire screen | Canvas size not properly anchored | Use anchor presets and proper offsets |
| Text not updating | Binding not set up correctly | Verify binding function returns correct type |
| Buttons not clickable | Input mode set to Game Only | Set Input Mode to Game and UI |
| Widget persists after level change | Not removed on EndPlay | Add Remove from Parent on level cleanup |
| Widget FPS drops | Tick-based bindings on complex widgets | Use event-driven updates instead |
