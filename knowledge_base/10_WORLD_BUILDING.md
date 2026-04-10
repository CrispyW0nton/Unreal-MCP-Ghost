# World Building — Complete Reference
> Source: Game Development with UE5 Volume 1 (Tiow Wee Tan), Mastering Technical Art in UE (Greg Penninck)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. World Partition System

**Automatically divides large worlds into streaming cells. Required for open-world games.**

### Setup
```
File → New Level → Open World (includes World Partition by default)
OR
Tools → Convert Level → Select existing level → Convert In-Place
```

### World Partition Editor
```
Window → World Partition
Shows the world grid with cells and their streaming status
```

### Key Settings (World Partition → Runtime Hash)
| Setting | Description | Typical Value |
|---------|-------------|--------------|
| `Cell Size` | Size of each streaming cell (cm) | 12800 (128m) |
| `Loading Range` | How far from player cells load | 25600 (256m) |
| `Z Culling` | Hide vertically obscured objects | Enabled |

### Actor HLOD (Hierarchical Level of Detail)
- Actors in World Partition can have auto-generated HLOD proxies
- Right-click actors → Build HLOD → proxies appear at distances

### One File Per Actor (OFPA)
- Each actor stored as its own .uasset file
- Enables proper collaborative work (Git doesn't conflict on individual actors)

---

## 2. Landscape System

### Creating a Landscape
```
Modes → Landscape → New Landscape
  Width/Height: 1009×1009 (or 2017×2017, 4033×4033 for larger)
  Sections per Component: 2×2 (more detail per component)
  Quads per Section: 63×63 (cell size in quads)
  Scale: 100 (1cm per quad by default)
```

### Importing a Heightmap
```
Landscape Mode → Import → Height Map File (.r16 / .raw / 16-bit PNG)
  Width: must match chosen landscape dimensions
  Scale: set Z scale to control cliff height
  Import button
```

### Landscape Tools
| Tool | Use |
|------|-----|
| Sculpt | Raise/lower terrain |
| Smooth | Blur height variations |
| Flatten | Level to specific height |
| Ramp | Create ramps between two points |
| Erosion | Simulate erosion |
| Hydro Erosion | Water-based erosion simulation |
| Noise | Add procedural height noise |
| Paint | Paint material layer blend weights |
| Manage | Add/remove landscape components |

### Landscape Layers (Material Painting)
```
Landscape Material uses Weight-Blended Layer (non-weight-blended = alpha layer):
  Layer: Grass (default)
  Layer: Rock
  Layer: Dirt
  Layer: Sand

In editor: Paint tool → select layer → paint on landscape
```

---

## 3. Auto-Blend Landscape Materials

**Auto-blend based on height and slope without manual painting.**

### Key Nodes
```
Height-Based Blend:
  Absolute World Position → Z → 
  Smooth Step (Min: 0, Max: 1000) → Alpha for Lerp

Slope-Based Blend:
  Vertex Normal WS → Slope Mask → 
  (Slope Angle threshold) → Alpha for rock/grass blend

Combined:
  HeightLerp (Grass bottom, Rock cliffs) →
  Slope Override (Snow on flat tops) →
  Output: Base Color, Normal, Roughness
```

### Material Layer Nodes (Layer Blend)
```
LandscapeLayerBlend node:
  Layer: Grass  → connect Grass material attributes
  Layer: Rock   → connect Rock material attributes
  Layer: Snow   → connect Snow material attributes
  
  Preview Weight: used in editor preview
  Blend Type: Weight Blend (painted) or Height Blend (auto by height)
```

---

## 4. Procedural Content Generation (PCG)

**Runtime or cook-time procedural placement using a graph-based system.**

### Enable Plugin
```
Edit → Plugins → Procedural Content Generation Framework → Enable
Restart editor
```

### Setup
1. Content Browser → PCG → PCG Graph Asset
2. Name: `PCG_DantooineVegetation`
3. Place `Procedural Content Generation Volume` in level
4. Assign PCG Graph to the volume's `Graph Instance` property
5. `Ctrl+R` to force regenerate

### Core PCG Nodes
| Node | Function |
|------|---------|
| `Input (Landscape/Mesh)` | Sample points from landscape or mesh |
| `Surface Sampler` | Distribute points on a surface |
| `Point Filter` | Filter by attribute (slope, density, etc.) |
| `Transform Points` | Randomize rotation, scale, offset |
| `Projection` | Project points onto surface |
| `Normal to Density` | Use surface normal to control density |
| `Density Filter` | Remove points below density threshold |
| `Self Pruning` | Remove points too close to each other |
| `Bounds Modifier` | Adjust point bounds for clearance |
| `Difference` | Remove points inside exclusion volumes |
| `Static Mesh Spawner` | Spawn static mesh at each point |
| `Spawn Actor` | Spawn Blueprint actor at each point |

### PCG Workflow — Dantooine Vegetation
```
[Landscape Input] → Surface Sampler (Density: 1.0/m²)
  → Point Filter (Slope < 30°)  ← no plants on steep slopes
  → Transform Points (Random Yaw, Scale 0.8–1.5)
  → Projection (snap to landscape surface)
  → Self Pruning (radius: 200cm)
  → Static Mesh Spawner (SM_Grass)
```

---

## 5. Runtime Virtual Textures (RVT)

**Blends assets seamlessly onto landscape using a shared virtual texture.**

### Setup
1. Content Browser → Materials → Runtime Virtual Texture
2. Configure: Base Color, Normal, Roughness, Specular
3. Add `Runtime Virtual Texture Volume` to level → set bounds to cover landscape
4. In `LandscapeStreamingProxy` Details → Draw Virtual Texture → Add RVT asset
5. In landscape material → add `Runtime Virtual Texture Output` node
6. In 3D asset material → add `Runtime Virtual Texture Sample` node

### RVT Blending in 3D Object Materials
```
Runtime Virtual Texture Sample → Base Color, Normal, Roughness
  BlendMaterialAttributes:
    Input A: Regular 3D object material
    Input B: Sampled from RVT (blends landscape texture into base of prop)
    Alpha: Blend amount (based on Object Bounds Z or vertex paint)
```

---

## 6. Lumen Global Illumination (Deep Reference)

### What Lumen Does
- Real-time GI: surfaces bounce light to illuminate shadowed areas
- Real-time reflections: any surface can reflect the scene
- No baking required — works with dynamic objects

### Lumen Settings (Post Process Volume)
```
Global Illumination:
  Method: Lumen
  Lumen Quality:
    Scene View Distance: 20000 (max GI contribution range)
    Scene Detail: 1 (surface detail tracing)
    Attenuation Radius: Auto
    Reflection Capture Radius: 1000

Reflections:
  Method: Lumen
  Quality: 1.0
  Max Roughness: 0.6 (rougher surfaces fall back to simpler reflection)
  Ray Lighting Mode: Surface Cache (fast) or Hit Lighting (accurate)

Software Ray Tracing Mode:
  Global Tracing (recommended for most cases)
  Detail Tracing (adds SDF tracing for small objects)
```

### Lumen Lighting Tips
- **Emissive multiplier**: must be ~40+ to contribute visible GI bounce
- **Post Process Film Slope**: 0.88 (good starting point for tone mapping)
- **Post Process Vignette**: 0.4 (subtle darkening at screen edges)
- **Exposure Metering Mode**: Auto Exposure Histogram for outdoor scenes

### Lumen Debugging
```
Console:
  r.Lumen.Visualize.SurfaceCache 1   → see surface cache coverage
  r.Lumen.Visualize.RadianceCache 1  → see radiance cache
  stat Lumen                          → timing breakdown
```

---

## 7. Lighting Types

| Light Type | Use | Dynamic | Static |
|------------|-----|---------|--------|
| **Directional Light** | Sun/moon; affects entire level | ✅ | ✅ |
| **Sky Light** | Ambient sky color; captures sky | ✅ | ✅ |
| **Point Light** | Spherical omni light | ✅ | ✅ |
| **Spot Light** | Cone-shaped directional light | ✅ | ✅ |
| **Rect Light** | Rectangular area light (windows, screens) | ✅ | ✅ |
| **Sky Atmosphere** | Physically-based sky and atmosphere | ✅ | — |
| **Volumetric Fog** | Foggy atmosphere with light shafts | ✅ | — |
| **Emissive Materials** | Glowing surfaces (Lumen picks up) | ✅ | — |

### Light Mobility
| Mobility | Cost | Dynamic Shadows | GI |
|----------|------|----------------|-----|
| **Static** | Free at runtime | ❌ (baked) | Baked lightmaps |
| **Stationary** | Low | ✅ (dynamic) | Baked indirect |
| **Dynamic (Movable)** | High | ✅ | Via Lumen only |

---

## 8. Collision System

### Collision Presets (Built-In)
| Preset | Profile |
|--------|---------|
| `BlockAll` | Blocks all channels |
| `BlockAllDynamic` | Blocks dynamic objects |
| `OverlapAll` | Overlaps everything |
| `OverlapAllDynamic` | Overlaps dynamic objects |
| `NoCollision` | No collision at all |
| `Trigger` | Overlaps all dynamic objects |
| `Pawn` | Standard character collision |
| `CharacterMesh` | Standard character mesh |
| `PhysicsActor` | Simulating physics object |

### Custom Collision Channels
```
Project Settings → Engine → Collision → New Trace Channel:
  Name: Interactable
  Default Response: Ignore
  
Then set specific meshes to "Block" the Interactable channel.
LineTraceByChannel uses ECC_Interactable as the channel.
```

---

## 9. World Building Best Practices

### Level Organization
```
Organize actors into Folders (in Outliner):
  Lighting/
    DirectionalLight_Sun
    SkyLight
    PostProcessVolume
  Landscape/
    Landscape
    NavMeshBoundsVolume
  Gameplay/
    BP_DantooineGameMode
    BP_DantooineQuestManager
  NPCs/
    BP_MasterJedi_01
    BP_RoamingNPC_StudentA_01
  Interactables/
    BP_LightsaberWorkbench_01
    BP_TrainingAreaTrigger_01
```

### Performance Targets
```
30 FPS (console): < 50 draw calls per frame
60 FPS (PC): < 200 draw calls per frame
VR 90 FPS: < 50 draw calls per eye

Use `stat SceneRendering` to check draw calls
Use `stat Unit` to check game thread / render thread / GPU times
```

### Level Streaming
```
For large levels:
  Place Level Streaming Volumes around areas
  Add sublevel: Window → Levels → + Level
  Set streaming mode: Blueprint (manual) or Volume (proximity)
  
  Load Level Instance:
    Load Level Instance (Level Name, Transform)
  
  Unload Level:
    Unload Streaming Level (Level Name)
```
