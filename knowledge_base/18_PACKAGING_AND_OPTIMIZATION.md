# Packaging, Build Settings, and Optimization
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Mastering Technical Art in UE (Greg Penninck), Game Development with UE5 Vol.1 (Tiow Wee Tan)
> Reference for shipping builds, build configurations, performance profiling, and all optimization strategies.

---

## 1. BUILD CONFIGURATIONS

### Configuration Types
| Configuration | Debug Info | Optimization | Use |
|---|---|---|---|
| `Debug` | Full | None | Step-through debugging; very slow |
| `DebugGame` | Full | Engine optimized | Debugging game code |
| `Development` | Partial | Partial | Daily development (default) |
| `Test` | None | Full | QA testing |
| `Shipping` | None | Full | Final release builds |

### Build Targets
| Target | Description |
|---|---|
| `Editor` | Development with editor UI (not shippable) |
| `Game` | Standalone game executable |
| `Server` | Dedicated server (no rendering) |
| `Client` | Client-only (no server logic) |

---

## 2. PROJECT SETTINGS FOR PACKAGING

### Maps & Modes
```
Project Settings → Maps & Modes
  → Default GameMode: BP_DantooineGameMode
  → Game Default Map: Dantooine_Level
  → Editor Startup Map: Dantooine_Level
  → Transition Map (optional)
```

### Project Description
```
Project Settings → Description
  → Project Name: "Enclave Project — Dantooine"
  → Description: "GAM270 Project 2"
  → Version: "1.0"
  → Company Name: "Academy of Art University"
  → Copyright Notice: "2026"
  → Homepage URL: ""
```

### Supported Platforms
```
Project Settings → Platforms
  → Windows: ✓ (primary target)
  → Mac: (if needed)
  → Mobile: (not for this project)
```

---

## 3. PACKAGING STEPS

### Verify Before Packaging
1. All Blueprints compile without errors (`Compile All` in toolbar)
2. All referenced assets exist (no broken references in Reference Viewer)
3. Default maps are set in Project Settings
4. No leftover test/debug actors in levels
5. Run a "Fix Up Redirectors" (in Content Browser, right-click root Content folder)

### Package the Project
```
File → Package Project → Windows (64-bit) → Choose output folder
```

### Key Packaging Options (Project Settings → Packaging)
| Setting | Recommended | Notes |
|---|---|---|
| Build Configuration | Shipping | Full optimization |
| Full Rebuild | false | Faster; only rebuilds changed files |
| For Distribution | true | Strips debug symbols |
| Compressed | true | Smaller pak files |
| Use Pak File | true | All content in one pak |
| Generate Chunks | false | (for download streaming only) |
| Cook All in Project | false | Only cook content actually used |
| List of Maps to Include | Dantooine_Level, (others) | Explicit list of levels |

### What Gets Cooked
- Only assets REFERENCED from the startup map and its dependencies
- Assets in the `Always Cook` list
- Assets tagged as Primary Asset Types in Asset Manager

---

## 4. PROFILING AND PERFORMANCE TOOLS

### In-Editor Profiling Commands
```bash
# Frame time breakdown
stat unit

# Frame rate
stat FPS

# Draw calls and mesh counts
stat scenerendering

# Memory usage
stat RHI

# GPU detailed breakdown (opens GPU visualizer)
ProfileGPU      # or Ctrl+Shift+,

# Disable particles temporarily
ShowFlag.Particles 0
ShowFlag.Particles 1

# Reduce resolution for performance testing
r.ScreenPercentage 50
r.ScreenPercentage 100
```

### Unreal Insights (External Tool)
- Launch from Editor: Tools → Run Unreal Insights
- Records CPU/GPU trace, Blueprint events, memory allocations
- Use for identifying frame hitches and slow Blueprint functions

### GPU Frame Debugger
1. `ProfileGPU` in console → Opens GPU Visualizer
2. Each render pass shows its cost in milliseconds
3. Identify expensive: Shadows, Translucency, Post Processing, Reflections

---

## 5. RENDERING OPTIMIZATION

### Draw Call Budget
- PC target: < 3000 draw calls per frame
- Each material on each mesh = 1 draw call
- Check with: `stat scenerendering` → `Mesh draw calls`

### Reducing Draw Calls
| Technique | Savings |
|---|---|
| Nanite | 1 draw call per material, unlimited triangles |
| Hierarchical LOD (HLOD) | Merge many actors into one at distance |
| Instanced Static Mesh (ISM) | Many copies = 1 draw call |
| Merge Actors | Combine static meshes in editor |
| Material Batching | Share materials across actors |

### Shader Complexity Viewmode
```
Viewport → Lit dropdown → Optimization Viewmodes → Shader Complexity
Green = cheap, Red = expensive, Pink = critically expensive
Target: mostly green/yellow in play areas
```

### Quad Overdraw Viewmode
```
Viewport → Lit → Optimization → Quad Overdraw
Bright areas = many transparent layers overlapping
Fix: reduce particle effects, simplify transparent materials
```

---

## 6. MEMORY OPTIMIZATION

### Texture Memory
| Budget | Platform |
|---|---|
| < 2 GB VRAM | Low spec / laptop |
| 4–6 GB VRAM | Mid-range PC (recommended target) |
| 8 GB+ VRAM | High-end PC / next-gen console |

### Texture Settings
```
Each texture asset → LOD Group → choose appropriate group:
  - UI: No mipmaps
  - World: WorldSpecular (trilinear)
  - Character: CharacterSpecular
  
Max Texture Size: cap large textures that don't need full resolution
Compression: BC1 (RGB no alpha), BC3 (RGBA), BC5 (normal maps), BC7 (HDR)
```

### ORM Texture Packing (from Greg Penninck)
```
Pack into one texture (reduces draw calls and memory):
  R Channel: Ambient Occlusion
  G Channel: Roughness  
  B Channel: Metallic

Name: T_AssetName_ORM.tga
Use BC1 compression (no alpha needed)
```

### Streaming Pool
If you see "Streaming Pool Over Budget" warnings:
```
Edit → Project Settings → Engine → Streaming → Pool Size
Increase from default (512 MB) to 1024 or 2048
```

---

## 7. LOD (LEVEL OF DETAIL) SYSTEM

### Static Mesh LODs
- LOD 0: Full detail (close up)
- LOD 1: 50% polygons (medium distance)
- LOD 2: 25% polygons (far away)
- LOD 3: 10% polygons (very far)
- Cull: hidden below a certain screen size

### Creating LODs
**Option A:** Auto LOD
```
Open Static Mesh → LOD Settings → Auto LOD Generation
→ Set desired polygon percentages per LOD level
→ Apply Changes
```

**Option B:** Nanite (recommended for static environment pieces)
```
Right-click mesh in Content Browser → Nanite → Enable Nanite
Nanite handles LOD automatically via virtualized geometry
```

### Screen Size Transitions
```
LOD 0: 1.0 screen size (close)
LOD 1: 0.25 screen size
LOD 2: 0.05 screen size
Cull: 0.01 screen size (invisible)
```

### Skeletal Mesh LODs
- Configured per-mesh under LOD → LOD Settings
- Important for NPCs: LOD 0 (nearby), LOD 1 (medium), LOD 2 (distant)

---

## 8. BLUEPRINT OPTIMIZATION RULES (EXPANDED)

### Blueprint Native Event vs Blueprint Event
- Native Events (from C++ parent) are faster than pure Blueprint events
- Override native events when possible (OnTakeDamage, BeginPlay)

### Minimize Blueprint Tick
| Blueprint Needs Tick? | Action |
|---|---|
| Movement, input processing | Yes — use Tick |
| AI state polling | No — use Timers (0.5s interval) |
| Animation state checks | No — use AnimNotify/Events |
| Health regen | No — use Timer (1.0s interval) |
| UI updates | No — use Event Dispatchers |

### Blueprint vs C++ Performance
```
For loops in Blueprint with 1000+ iterations: SLOW
Same loop in C++: ~100x faster

Workaround: Use exec_python for bulk data processing when in editor
At runtime: Keep loops small (<100 items in Blueprint)
```

### Blueprint Nativization (Legacy — UE5.2+)
> Note: Blueprint Nativization was deprecated in UE5.2. C++ is the correct solution for performance-critical code.

---

## 9. NANITE GUIDELINES (EXPANDED)

### What Nanite Can Do
- Handle billions of triangles with minimal CPU overhead
- Eliminate manual LOD creation for supported meshes
- Merge many draw calls into unified geometry pipeline

### Nanite Limitations
| Not Supported | Alternative |
|---|---|
| Skeletal Meshes | Traditional LOD + skinned mesh optimization |
| World Position Offset materials | Standard materials only |
| Two-sided materials (Masked) | Separate back-face mesh |
| Tessellation | Nanite handles detail natively |
| Translucent/Additive | Use non-Nanite meshes |
| Very small meshes (<100 tris) | Just use regular LOD |

### Enabling Nanite
```
Select meshes in Content Browser
Right-click → Nanite → Enable Nanite
File → Save All

Verify in Static Mesh Editor: Details → Nanite Settings → Enabled checkbox
```

---

## 10. LUMEN PERFORMANCE GUIDE

### Lumen Quality Settings
```
PostProcessVolume → Lumen Global Illumination
  → Method: Lumen (automatic)
  → Final Gather Quality: 1.0 (performance) to 4.0 (quality)
  → Max Trace Distance: 5000 (larger = more indirect light reach)
  → Scene Capture Size: 64 (faster) to 256 (higher quality)
  
Lumen Reflections:
  → Quality: 1.0 to 4.0
  → Ray Lighting Mode: Surface Cache (fast) vs Hit Lighting (accurate)
```

### Software vs Hardware Ray Tracing
| Mode | Hardware Need | Quality | Performance |
|------|--------------|---------|-------------|
| Software RT (Global) | Any GPU | Good | Best |
| Software RT (Detail) | Any GPU | Better (uses SDFs) | Medium |
| Hardware RT | NVIDIA RTX / AMD RDNA2+ | Best | Most expensive |

### Console Commands for Lumen Debugging
```
stat Lumen            # Lumen frame timing
r.Lumen.Reflections.Allow 0   # Disable reflections for testing
r.Lumen.GI.Allow 0            # Disable GI for testing
r.Lumen.Quality 1              # Set quality level (0-4)
```

---

## 11. ASSET NAMING CONVENTION (FULL REFERENCE)

| Asset Type | Prefix | Example |
|---|---|---|
| Blueprint | `BP_` | `BP_PlayerJediCharacter` |
| Widget Blueprint | `WBP_` | `WBP_HUD` |
| Animation Blueprint | `ABP_` | `ABP_PlayerJedi` |
| Behavior Tree | `BT_` | `BT_RoamingNPC` |
| Blackboard | `BB_` | `BB_RoamingNPC` |
| BT Task | `BTT_` | `BTT_FindRandomPatrol` |
| BT Decorator | `BTD_` | `BTD_IsPlayerNearby` |
| BT Service | `BTS_` | `BTS_UpdateTargetDistance` |
| AI Controller BP | `BP_` + `_AIController` | `BP_NPC_AIController` |
| Material | `M_` | `M_Rock_Dantooine` |
| Material Instance | `MI_` | `MI_Rock_Mossy` |
| Material Function | `MF_` | `MF_NormalBlend` |
| Texture | `T_` | `T_Rock_BaseColor` |
| ORM Texture | `T_` + `_ORM` | `T_Rock_ORM` |
| Niagara System | `NS_` | `NS_SaberGlow` |
| Niagara Emitter | `NE_` | `NE_GlowParticles` |
| Skeletal Mesh | `SK_` | `SK_PlayerJedi` |
| Static Mesh | `SM_` | `SM_LightsaberWorkbench` |
| Skeleton | `SKEL_` | `SKEL_PlayerJedi` |
| Physics Asset | `PHYS_` | `PHYS_PlayerJedi` |
| Animation Sequence | `AN_` | `AN_Player_Walk` |
| Blend Space | `BS_` | `BS_JediLocomotion` |
| Aim Offset | `AO_` | `AO_JediAim` |
| Animation Montage | `AM_` | `AM_Attack_Swing` |
| Enum | `E_` | `E_QuestStage` |
| Struct | `ST_` | `ST_DialogueLine` |
| Interface | `BPI_` | `BPI_Interactable` |
| Blueprint Func Lib | `BFL_` | `BFL_DantooineHelpers` |
| Data Table | `DT_` | `DT_DialogueLines` |
| Data Asset | `DA_` | `DA_LightsaberConfig` |
| Input Action | `IA_` | `IA_Attack` |
| Input Mapping Context | `IMC_` | `IMC_Dantooine` |
| Level | (no prefix or `L_`) | `Dantooine_Level` |
| Level Sequence | `LS_` | `LS_LightsaberBuild` |
| Sound Cue | `SC_` | `SC_SaberHum` |
| Sound Wave | `SW_` or `SFX_` | `SFX_Saber_Swing` |
| Save Game BP | `BP_` + `GameSave` | `BP_DantooineGameSave` |
| Game Instance BP | `BP_` + `GameInstance` | `BP_DantooineGameInstance` |

---

## 12. COMMON BUILD ERRORS AND FIXES

| Error | Cause | Fix |
|---|---|---|
| "No Source Code" error | Blueprint-only project missing C++ | Add blank C++ class: `File → New C++ Class` → None (empty) |
| Build.bat exits code 6 | Missing .NET SDK or Visual Studio | Install Visual Studio 2022 with C++ game workload |
| Missing redirectors | Assets were moved without Fix Up | Right-click Content folder → Fix Up Redirectors |
| Unresolved blueprint references | Asset deleted but still referenced | Find references (right-click → Reference Viewer), then re-wire |
| Cook errors | Asset has missing dependencies | Delete and recreate the asset, check for invalid references |
| Shader compile errors | Material node incompatibility | Check material preview — red = error; check node types |
