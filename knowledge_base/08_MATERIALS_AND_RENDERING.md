# Materials, Rendering, and Technical Art
> Source: Mastering Technical Art in UE (Greg Penninck, Ch1-15), UE5 Game Dev Vol.1 (Tiow Wee Tan, Ch3-5)
> Version: UE 5.6.1 | Updated: 2026-04-10

---

## 1. Rendering Pipeline Overview (Ch2 Penninck)

### Deferred Rendering (UE5 Default)
UE5 uses **deferred rendering** — separates geometry and lighting into multiple passes:
1. **Geometry Pass**: All visible meshes write to the G-Buffer (not rendered yet)
2. **Lighting Pass**: G-Buffer data is used to calculate all lights at once
3. **Post-Processing Pass**: Bloom, DOF, color grading, etc.

**G-Buffer Contents**: Base Color, Depth, Metallic, Roughness, Normals, Specular, Custom Data

**Strengths**: Many lights with low cost; supports complex lighting scenarios  
**Weaknesses**: Transparency is expensive; high memory cost for G-Buffer

---

## 2. Physically Based Rendering (PBR)

**PBR tries to accurately represent how materials interact with light in the real world.**

### Four Key PBR Attributes in UE5
| Attribute | Range | Description |
|---|---|---|
| **Base Color** | 0.0–1.0 RGB | The diffuse color of the surface (no lighting); for metals: reflection color |
| **Roughness** | 0.0–1.0 | 0 = mirror-smooth; 1 = rough/matte |
| **Metallic** | 0 or 1 | 0 = dielectric (non-metal); 1 = metallic. Rarely use values between. |
| **Specular** | 0.0–1.0 | Specular contribution; default 0.5 (rarely adjusted) |

**Also common in materials:**
- **Normal** — Surface detail direction map (tangent-space normals, mostly blue)
- **Ambient Occlusion (AO)** — Baked shadow data in crevices
- **Emissive Color** — Self-illumination (light source materials)
- **Opacity** — Transparency (only for Translucent or Masked blend modes)

### ORM Texture Convention (Penninck)
Pack multiple PBR maps into one RGB texture to save texture sampler budget:
- **R channel** = Ambient Occlusion
- **G channel** = Roughness
- **B channel** = Metallic

Name convention: `T_AssetName_ORM` — enables material to use 1 texture for 3 channels.

---

## 3. Material Editor Basics

### Opening a Material
- Double-click any Material (M_*) or Material Instance (MI_*) asset

### Material Editor Layout
- **Graph**: Node-based visual scripting for material logic
- **Details**: Properties of selected node or the material itself
- **Preview**: Real-time 3D preview of material on mesh
- **Palette**: Searchable list of all available nodes

### The Main Material Node
All graph paths must connect to the central `Result` node pins:
- `Base Color`, `Metallic`, `Specular`, `Roughness`, `Emissive Color`, `Opacity`, `Normal`, `AO`, `World Position Offset`, etc.

### Key Material Nodes

| Node | Function |
|---|---|
| **Texture Sample** | Samples a texture; R/G/B/A/RGB outputs |
| **Texture Sample Parameter 2D** | Sampler with a named parameter (exposed to instances) |
| **Scalar Parameter** | Float parameter exposed to instances |
| **Vector Parameter** | Color/vector parameter exposed to instances |
| **Constant** | Fixed float value |
| **Constant3Vector** | Fixed RGB color |
| **Multiply** | Multiplies two values (A * B); darkens textures |
| **Add** | Adds two values (A + B); brightens textures |
| **Lerp** | Linear interpolate between A and B by Alpha |
| **One Minus** | 1 - value (inverts 0→1 range) |
| **Power** | Raises to exponent (good for contrast control) |
| **Component Mask** | Extracts R, G, B, or A channels |
| **Append** | Combines channels (R+G → RG vector) |
| **Saturate** | Clamps value to 0–1 range |
| **TextureCoordinate (UV)** | Raw UV coordinates; use to control tiling |
| **Panner** | Animates UVs in direction; use for scrolling textures (water, lava) |
| **Rotator** | Rotates UVs around a pivot point |
| **World Position** | World-space position of pixel; use for world-space effects |
| **Fresnel** | Rim/edge effect based on viewing angle |
| **Depth Fade** | Soft particle edges near geometry |
| **Particle Color** | Receives color data from Niagara particle |
| **Dynamic Parameter** | Receives float data from Niagara particle system |
| **Named Reroute Declaration** | Creates a named reroute node for clean graph organization |

### Material Math Patterns
```
Tint a texture: Texture RGB × Color Parameter = Tinted result
Increase contrast: Power(GreyscaleValue, 2.0) = More contrast
Combine two textures: Lerp(Texture A, Texture B, BlendMask)
Invert roughness for wetness: 1 - WetnessFloat = lower roughness
Scale UV tiling: TextureCoordinate × TilingScalar = more repetitions
```

---

## 4. Material Properties

### Material Domain
| Domain | Use Case |
|---|---|
| **Surface** | Standard 3D surface (default) |
| **Deferred Decal** | Projects onto surfaces; must use Translucent/Modulate blend |
| **Light Function** | Applied to lights to shape light pattern |
| **Post Process** | Applied to post-process volumes for screen effects |
| **User Interface** | For UMG/Slate UI elements |
| **Volume** | For volumetric materials |

### Blend Mode
| Mode | Description | Use Case |
|---|---|---|
| **Opaque** | Fully solid; no transparency | Most game meshes |
| **Masked** | Binary transparency using Opacity Mask | Foliage, chain-link fences |
| **Translucent** | Full alpha blending; expensive | Glass, water, VFX |
| **Additive** | Adds color on top; no occlusion | Fire, glow, energy effects |
| **Modulate** | Multiplies; darkens background | Tinted glass, decals |

### Shading Model
| Model | Use Case |
|---|---|
| **Default Lit** | Standard PBR shading |
| **Unlit** | No lighting; emissive only |
| **Subsurface** | Skin, wax, marble — translucent scattering |
| **Subsurface Profile** | High-quality skin |
| **Clear Coat** | Car paint, lacquered wood |
| **Two Sided Foliage** | Plants where light passes through leaves |
| **Hair** | Strand-based hair anisotropic shading |
| **Cloth** | Fabric materials |
| **Eye** | Realistic eye rendering |

---

## 5. Material Instances (Ch5 Penninck)

**Material Instances inherit from a parent Material and allow overriding exposed parameters without recompiling.**

### Why Use Material Instances
- Fast to create variations (no shader recompile)
- Can override on a per-instance basis in the level editor
- Reduce unique material count → fewer shader variants

### Creating a Material Instance
1. Right-click a Material → Create Material Instance
2. Naming: `MI_CharacterName_Color` or `MI_BaseMaster_Rock`

### Creating Parameters in Parent Material
- Right-click a `Constant` node → Convert to Parameter → name it
- Or right-click any node input → Promote to Parameter
- **Scalar Parameter**: exposed float value
- **Vector Parameter**: exposed color/vector value
- **Texture Parameter 2D**: exposed texture slot

### Parameter Groups and Sort Priority
- Assign `Group` in parameter Details (e.g., "Albedo", "Normal", "Roughness Controls")
- `Sort Priority` controls order within a group (higher number = appears lower in list)

### Override in Material Instance Editor
- Check the checkbox next to a parameter to enable override
- Uncheck to revert to parent value

---

## 6. Master Materials (Ch6 Penninck)

**A single base material that covers many use cases through parameters.**

### Master Material Design Principles
1. **Single source of truth**: One M_BaseMaster for all opaque props
2. **Parameters for everything**: No hardcoded values
3. **Artist-friendly naming**: Self-documenting parameter names
4. **Grouped parameters**: Texture group, Color group, Roughness Controls, etc.

### Standard Master Material Structure (M_BaseMaster)
```
[Base Color Texture Param] × [Tint Color Param] → Base Color
[ORM Texture Param] → R → AO
                    → G × [Roughness Scale] → Roughness
                    → B × [Metallic Scale] → Metallic  
[Specular Param] → Specular
[Normal Map Param] × [Normal Intensity] → Normal
```

### Tiling Master Material (M_TilingMaster)
For surfaces that tile (floors, walls):
```
[TextureCoordinate] × [Tiling Scale Param] → UV
[Diffuse Texture Param] sampled at scaled UV → Base Color
[Normal Detail Texture] at higher tiling → blended with main normal
[Roughness variation texture] for surface detail
```

### Emissive Master Material (M_EmissiveMaster)
For light-emitting surfaces:
```
[Emissive Texture Param] × [Emissive Color Param] × [Emissive Intensity] → Emissive Color
[Base Color Texture Param] → Base Color
```

### Translucent Master Material (M_TranslucentMaster)
For glass, crystals:
```
Blend Mode: Translucent
Shading Model: Default Lit (or Subsurface for thick glass)
[Opacity Param] → Opacity
[Refraction Param] → Refraction
```

---

## 7. Mesh Painting and Vertex Colors (Ch7 Penninck)

**Paint colors directly onto mesh vertices in the editor. Driven by Vertex Color node in material.**

### Vertex Color Node Outputs
- **R, G, B** — Individual color channels (0–1 scalars)
- **A** — Alpha channel
- **RGBA** — Combined color

### Mesh Paint Material Setup
```
[Vertex Color] → R → Lerp Alpha
  → Lerp (A = Texture1 RGB, B = Texture2 RGB, Alpha = R channel)
  → Base Color
```

### Mesh Paint Workflow
1. Select a mesh in the level
2. Mode → Mesh Paint (or top toolbar Paint icon in UE5)
3. Set Paint Type = Vertex
4. Choose channel (Red, Green, Blue, or Alpha)
5. Set Paint Color = 1.0 (white) to paint, 0.0 (black) to erase
6. Brush size, strength, falloff adjustable
7. Press X to swap paint/erase colors

**Requirement**: Mesh must have sufficient vertex count in areas being painted; subdivide in DCC if needed.

### Per-Layer PBR Controls
Advanced mesh paint materials can have separate Roughness, Metallic, Normal per layer:
```
Layer 0 (Rock): Rock_ORM.R→AO, Rock_ORM.G→Roughness, Rock_ORM.B→Metallic
Layer 1 (Moss): Moss_ORM similar
Vertex R channel → Lerp all Layer 0 vs Layer 1 values
```

---

## 8. Decal Materials (Ch7 Penninck)

**Project onto existing surfaces without modifying the mesh.**

### Decal Material Setup
1. Create a Material
2. Details panel → **Material Domain** = `Deferred Decal`
3. Details panel → **Blend Mode** = `Translucent` (or `Modulate`)
4. Set up Base Color and Normal (Opacity controls decal strength)

### Decal Blend Modes
| Mode | Effect |
|---|---|
| **Translucent** | Full color override; use for dirt, paint |
| **Stain** | Multiplies on color; darkens surface |
| **Normal** | Only affects Normal channel |
| **Emissive** | Only affects emissive channel |
| **Modulate** | Multiplies base color |

### Decal Actor
- Place a Decal Actor in the level (or use a Decal component)
- Assign the decal material
- Scale the Decal Actor box to control projection area
- White arrow indicates projection direction

### Mesh Decal
- Set a material as Deferred Decal on a simple plane mesh
- Attach to animated mesh for moving decals (blood stains, footprints)

---

## 9. VFX Materials (Ch8 Penninck)

**Two fundamental VFX master materials needed for all particle effects.**

### M_VFXTrans (Translucent)
```
Material Domain: Surface
Blend Mode: Translucent
Shading Model: Unlit (or Default Lit for lighting-reactive)

[Texture Param] RGB × [Particle Color] RGB → Base Color
[Texture Param] A × [Particle Color] A → Opacity
```
Use for: Smoke, fog, soft glow effects

### M_VFXAdd (Additive)
```
Material Domain: Surface
Blend Mode: Additive
Shading Model: Unlit

[Texture Param] RGB × [Particle Color] RGB → Emissive Color
[Texture Param] A × [Particle Color] A × [Intensity Param] → Opacity
```
Use for: Fire, electricity, energy effects, sparks

### Particle Color Node
- Receives RGBA color set by Niagara's `Initialize Particle` or `Color` module
- Must connect RGB to Base Color or Emissive, A to Opacity
- Allows Niagara to drive color without material recompile

### Panning (Scrolling Animation)
```
[TextureCoordinate] → Panner (Speed X, Speed Y from Params) → Texture Sample UV
```
Creates scrolling texture for flames, water, energy streams.

### UV Distortion
```
Distortion texture → Component Mask R+G → * DistortionStrength → + Primary UV
→ Distorted UV → Main Texture Sample
```

### Dynamic Parameters
- Created in Material: right-click → Dynamic Parameter → names 4 float channels (Param0, Param1, Param2, Param3)
- Driven from Niagara module `Dynamic Material Parameters` — bind Niagara attributes to each channel
- Use for: opacity fade over lifetime, size-to-color correlation

### Value Step / Smooth Step (Erosion Pattern)
```
# Hard cutoff fade:
[Particle Lifetime Alpha] → Value Step (Cutoff from Param) → Opacity
Result: Particle pops out at threshold instead of fading smoothly

# Soft edge fade (Smooth Step):
[Lifetime Alpha] → Smooth Step (Min, Max) → Opacity
Result: S-curve fade between min and max values
```

### Sub UV Animation
```
[SubUV Texture (4x4 or 8x8 grid)] → Texture Sample with Sub UV parameters
→ Use SubUV Flipbook node or particle's Sub UV module
```
Sub UV sheets: sprite sheet with multiple frames; particle cycles through them for animated effects.

---

## 10. Rendering Optimization (Ch2 Penninck)

### Draw Call Management
**Console commands to monitor:**
```
stat scenerendering    — shows draw call count and scene info
stat RHI               — lower level rendering stats
stat GPU               — GPU timing per pass
ProfileGPU             — (or Ctrl+Shift+,) detailed GPU visualizer
```

**Rough draw call budgets:**
- Mobile: a few hundred
- PC/Console: 3,000–5,000
- High-spec workstation: up to 10,000

**How to reduce draw calls:**
1. Limit unique materials per mesh (each material = 1 draw call)
2. Use Instanced Static Meshes (ISM/HISM) for repeated geometry
3. Enable Nanite on high-poly static meshes (reduces to 1 draw call per material)
4. Use HLOD (Hierarchical LOD) for background clusters
5. Merge static meshes that are always visible together

### Shader Complexity
**View in editor:** Lit button → Optimization Viewmodes → Shader Complexity
- Green = cheap; Yellow = moderate; Red = expensive; White = very expensive

**Reduce complexity:**
- Avoid noise procedural nodes (use baked textures instead)
- Avoid complex math on transparency
- Reduce texture sampler count

**View instruction count:** Material Editor → Window → Stats

### Overdraw
**View in editor:** Lit button → Optimization Viewmodes → Quad Overdraw
- Dark blue = no overdraw; Green → Yellow → Red → White = increasing overdraw

**Reduce overdraw:**
- Use Masked instead of Translucent where possible
- Reduce particle count
- Reduce size of transparent objects on screen
- Use opaque/masked geometry instead of alpha textures (e.g., 3D grass mesh vs alpha plane)

### Memory Management
**View texture memory:** Tools → Audit → Statistics → switch to Texture Stats
**Reduce texture size:** Open texture → Details → Max Texture Size (1024, 512, 256)
**Batch change:** Select multiple textures → right-click → Asset Actions → Edit Selection in Property Matrix

**Texture resolution guide:**
- Hero character: up to 4096
- Background prop: 512–1024
- Small prop: 256–512
- Rule: texel density (512 pixels per meter squared is a common standard)

### GPU Profiler
`Ctrl+Shift+,` or type `ProfileGPU` in console → GPU Visualizer shows:
- Time spent per rendering stage (Shadow Depths, Base Pass, Lighting, Translucency, Post Process)
- Expand to see individual actors' costs
- Useful for identifying specific problem actors/materials

---

## 11. Nanite

**UE5's virtualized geometry system. Near-unlimited polygon count for supported meshes.**

### Enabling Nanite
1. Select a Static Mesh asset in Content Browser
2. Double-click to open → Details → Nanite → **Enable Nanite Support = true**
3. Or right-click → Nanite → Enable

### Nanite Benefits
- One draw call per material regardless of polygon count
- No manual LOD setup required
- Supports high detail close-up and distant views

### Nanite Limitations
- Does NOT support: Skeletal Meshes, Landscape, transparent materials, some deformation
- Has a small CPU cost (1 draw call per material in scene)
- Requires `r.Nanite 1` in project (enabled by default in UE5)

### Workflow for Quixel Megascans
1. Import Megascans asset via Quixel Bridge
2. Check "Enable Nanite" checkbox during import
3. Done — no further LOD work needed

---

## 12. Lumen (from Tiow Wee Tan Ch6)

**UE5's dynamic global illumination and reflection system. No baking required.**

### Enabling Lumen
1. Project Settings → Rendering → Global Illumination → Method = Lumen
2. Project Settings → Rendering → Reflections → Method = Lumen

### Lumen Configuration
| Setting | Value | Effect |
|---|---|---|
| Software Ray Tracing Mode | Global Tracing | Best quality |
| Final Gather Quality | 1 | Default quality |
| Max Trace Distance | 20000 | How far indirect light travels |
| Scene Lighting Update Speed | 4 | Higher = faster light updates (more GPU cost) |

### Lumen with Emissive Materials
- Set Emissive Color in Material (e.g., Emissive Texture × 40 intensity)
- Lumen automatically uses emissive as a light source
- Avoid extremely high emissive values (causes color bleeding)

### Post-Process Volume — Lumen Settings
In a Post-Process Volume (Infinite Extent):
- Global Illumination → Lumen → Indirect Lighting Intensity, Sky Light Leaking
- Reflections → Lumen → Quality, Max Roughness

### Performance
- Requires DX12 or Vulkan (not DX11 or mobile)
- Works best at 1080p+
- Profile with: `stat Lumen`

---

## 13. Runtime Virtual Textures (RVT) (from Tiow Wee Tan Ch5)

**Cache landscape shading for objects that sit on the landscape to blend seamlessly.**

### What RVT Does
- Renders the landscape into a virtual texture
- Assets on the landscape sample this texture to match surrounding colors
- Creates seamless blending between landscape and placed assets

### RVT Setup
1. Create RVT asset (Content Browser → Add → Texture → Runtime Virtual Texture)
   - Configure: Base Color + Normal + Roughness/Specular; or World Height
2. Add `Runtime Virtual Texture Volume` to level → assign RVT asset to it
3. In each Landscape Streaming Proxy: Details → `Draw in Virtual Textures` → add RVT asset
4. In Landscape Material: add `Runtime Virtual Texture Output` node (writes landscape data)
5. In rock/foliage materials: add `Runtime Virtual Texture Sample` → blend with asset color

### RVT Material Nodes
- `Runtime Virtual Texture Output` — writes pixel data to the RVT (use in landscape material)
- `Runtime Virtual Texture Sample Parameter` — reads from RVT (use in asset materials)
- `Transform(Vector, WorldToTangent)` — convert RVT normal to tangent space

---

## 14. Landscape Auto-Blend Materials (from Tiow Wee Tan Ch3)

**Automatically blend different textures based on height and slope.**

### Height-Based Blending Nodes
```
[Absolute World Position] → Component Mask (Z only) → A
[Transition Height Param] → B
[Transition Range Param] → Alpha
→ SmoothStep (A, B, Alpha) or custom math → Lerp Alpha between layers
```

### Slope-Based Blending
- `World Normal` node → Z component → cliff areas have low Z value
- `SlopeMask` — dedicated node for slope detection (angle threshold, smoothness)

### Material Layer Blend
- `MatLayerBlend_Standard` — proper material layer blending for landscape
- Each layer: its own Base Color, Normal, Roughness
- Blend alpha from height/slope calculation

### Named Reroute Node
- Right-click → Add Named Reroute Declaration → name it
- Use as a clean wire connection alias (avoids spaghetti across large material graphs)
- Multiple Named Reroute Usage nodes can connect to the same Declaration

---

## 15. Key Material Nodes Quick Reference

| Node | Category | Key Use |
|---|---|---|
| `Texture Sample 2D` | Texture | Main texture sampler |
| `TextureCoordinate` | Coordinates | UV tiling control |
| `Panner` | Coordinates | Animated UV scrolling |
| `World Position` | Coordinates | World-space effects |
| `Lerp` | Math | Blend between two values |
| `Multiply` | Math | Darken/scale values |
| `Add` | Math | Brighten/combine |
| `Power` | Math | Contrast control |
| `Saturate` | Math | Clamp 0–1 |
| `Fresnel` | Math | Edge/rim glow |
| `Component Mask` | Utility | Extract R/G/B/A channel |
| `Append` | Utility | Build vectors from channels |
| `Particle Color` | VFX | Receive Niagara color |
| `Dynamic Parameter` | VFX | Receive Niagara float data |
| `Vertex Color` | Painting | Per-vertex painted data |
| `Named Reroute` | Organization | Clean graph wiring |
| `Comment` | Organization | Color-coded group labels |
