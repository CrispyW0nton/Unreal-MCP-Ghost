# Niagara VFX System — Complete Reference
> Source: Mastering Technical Art in Unreal Engine (Greg Penninck), Game Development with UE5 Vol.1 (Tiow Wee Tan)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. Niagara Hierarchy

```
Niagara System (NS_)
  └── Emitter (one or more emitters)
        ├── Emitter Update (per-frame emitter logic)
        │     └── Modules: Emitter State, Spawn Rate, Spawn Burst...
        ├── Particle Spawn (runs once per new particle)
        │     └── Modules: Initialize Particle, Shape Location...
        ├── Particle Update (runs every frame per particle)
        │     └── Modules: Apply Forces, Scale Color, Scale Size...
        └── Renderer (visual output)
              └── Sprite / Mesh / Ribbon / Light Renderer
```

---

## 2. Simulation Targets

| Target | Use | Notes |
|--------|-----|-------|
| **CPU Simulation** | Complex logic, collision, events, BPs | Max ~10k particles |
| **GPU Simulation** | Massive counts (fire, smoke, explosions) | Requires Fixed Bounds |

**Fixed Bounds (Required for GPU):**
- In Emitter settings: enable **Fixed Bounds**
- Set to box size larger than your effect
- Without Fixed Bounds, GPU emitters will disappear when off-screen

---

## 3. Module Reference — Complete List

### Emitter Update Modules
| Module | Key Parameters | Purpose |
|--------|---------------|---------|
| `Emitter State` | Loop Duration, Loop Count | Emitter lifetime/looping |
| `Spawn Rate` | Spawn Rate (float) | Continuous particles/second |
| `Spawn Burst Instantaneous` | Count, Burst Timing | Spawn N particles at once |
| `Spawn Per Unit` | Spawn Per Unit, movement threshold | Spawn based on movement |

### Particle Spawn Modules
| Module | Key Parameters | Purpose |
|--------|---------------|---------|
| `Initialize Particle` | Lifetime (min/max), Sprite Size Mode, Color Mode, Mass | Basic particle setup |
| `Shape Location: Sphere` | Sphere Radius, Surface Only | Spawn in sphere volume |
| `Shape Location: Ring/Disc` | Ring Radius, Ring Width | Spawn in ring pattern |
| `Shape Location: Box` | Box Size | Spawn in box volume |
| `Shape Location: Cylinder` | Height, Radius | Spawn in cylinder |
| `Add Velocity` | Speed (min/max), Velocity Mode (linear/in-cone) | Initial particle velocity |
| `Add Velocity: In Cone` | Cone Angle, Speed | Directional emission |
| `Add Velocity: From Point` | Origin, Speed | Radial from point |
| `Sub UV Animation` | Start Frame, End Frame, Playback Mode | Flipbook/sprite sheet |
| `Jitter Position` | Jitter Amount | Random positional scatter |
| `Calculate Accurate Velocity` | — | Derives velocity from position delta |

### Particle Update Modules
| Module | Key Parameters | Purpose |
|--------|---------------|---------|
| `Curl Noise Force` | Noise Strength (1000–5000), Noise Frequency, Pan Noise Field | Turbulent swirling motion |
| `Vortex Force` | Force Amount, Origin Pull Strength | Spiral toward center |
| `Drag` | Drag coefficient | Slow particles over time |
| `Gravity Force` | Z force (default -980) | Gravity |
| `Point Attraction Force` | Attraction Strength, Radius | Pull toward point |
| `Scale Color` | Color Curve (over Normalized Age) | Fade in/out, color shift |
| `Scale Sprite Size` | Size Curve | Grow/shrink over lifetime |
| `Scale Sprite Size by Speed` | Velocity range, Size range | Size based on how fast |
| `Sprite Rotation Rate` | Rate (degrees/second) | Spinning sprites |
| `Collision` | Restitution, Friction, CPU Collision Trace Channel | Bounce off surfaces |
| `Generate Collision Event` | Delay | Fire event on first collision |
| `Kill Particles in Volume` | Volume bounds | Remove particles outside area |
| `Update Mesh Orientation` | — | Keep mesh particles facing direction |
| `Ribbon Width` | Width Curve | Ribbon thickness over lifetime |
| `Dynamic Material Parameters` | Parameter Name, Value | Send values to particle material |

### Event Modules
| Module | Purpose |
|--------|---------|
| `Generate Collision Event` | Fires collision event on impact |
| `Event Handler: Receive Collision` | React to collision events from same/other emitters |
| `Generate Location Event` | Fires event at particle location |
| `Receive Location Event` | Spawn new particles at received locations |

---

## 4. Renderer Types

### Sprite Renderer
- Renders 2D camera-facing quads
- Key properties:
  - `Alignment: Face Camera` — always face viewer
  - `Sub UV Layout` — SubUV grid for flipbook animation (e.g., 8×8 = 64 frames)
  - `Material` — the sprite material

### Mesh Renderer
- Renders 3D static meshes per particle
- Key properties:
  - `Particle Mesh` — the static mesh to render
  - `Override Materials` — use particle-controlled materials
  - Scale driven by Particle Size variable

### Ribbon Renderer
- Renders connected trail between particles (sorted by age/id)
- Key properties:
  - `Ribbon Width` — driven by Scale Sprite Size or Ribbon Width module
  - `Facing Mode` — how ribbon faces the camera
  - Material: use Ribbon UV coordinates

### Light Renderer
- Renders dynamic point lights per particle
- Key properties:
  - `Radius Scale` — drives light radius
  - `Color/Intensity` — driven by particle color
  - **Very expensive** — use sparingly (<100 light particles)

---

## 5. VFX Recipes — Dantooine Project

### Lightsaber Trail (NS_SaberTrail)
```
Emitter Type: CPU Sim
Renderer: Ribbon

Emitter Update:
  Emitter State: Loop Infinite, Loops = 0
  
Particle Spawn:
  Initialize Particle: Lifetime = 0.1, Sprite Size = (10, 10)
  
Particle Update:
  Scale Sprite Size: 1.0 → 0.0 over age (fade out)
  Scale Color: Alpha 1→0 over lifetime

Material: M_SaberTrail
  Use Ribbon UV
  Additive blend mode
  Emissive color from Particle Color
```

### Workbench Sparks (NS_WorkbenchSparks)
```
Emitter Type: CPU Sim (for collision)
Renderer: Sprite

Emitter Update:
  Spawn Burst Instantaneous: Count = 50, Burst Time = 0
  
Particle Spawn:
  Initialize Particle: Lifetime = (0.5–1.5), Sprite Size = (2, 2)
  Shape Location: Sphere Radius = 20
  Add Velocity: In Cone (Speed = 200–500, Cone Angle = 90)
  
Particle Update:
  Gravity Force: Z = -980
  Collision: Restitution = 0.3, CPU Collision
  Scale Color: Yellow → Orange → Black over age
  Scale Sprite Size: 1→0 over age

Material: M_SparkParticle
  Emissive only, Additive blend
```

### Level Complete VFX (NS_LevelComplete)
```
Emitter Type: GPU Sim
Renderer: Sprite (Sub UV flipbook)

Emitter Update:
  Spawn Burst Instantaneous: Count = 300
  
Particle Spawn:
  Initialize Particle: Lifetime = 2–4s, Sprite Size = (50–150)
  Shape Location: Sphere Radius = 500, Surface Only
  Add Velocity: From Point (Speed = 200–1000, Origin = (0,0,0))
  
Particle Update:
  Curl Noise Force: Strength = 2000, Frequency = 0.5
  Gravity Force: Z = -100 (slow drift)
  Scale Color: RGB curve = rainbow over lifetime, Alpha = 1→0
  Scale Sprite Size: 0→1→0 (pop in, pop out)
  Sub UV Animation: 8×8 grid, Age Sequential

Fixed Bounds: 2000×2000×2000
```

### Saber Glow (NS_SaberGlow)
```
Emitter Type: GPU Sim
Renderer: Sprite + Light Renderer

Particle Spawn:
  Initialize Particle: Lifetime = 0.05 (very short, continuous)
  Shape Location: Cylinder (blade shape)
  
Particle Update:
  Scale Color: Emissive glow color
  
Renderer 1: Sprite (Additive, glow material)
Renderer 2: Light (small radius, high intensity, color matches saber)
```

---

## 6. Using Niagara in Blueprints

### Spawn a Niagara Effect
```
Spawn System at Location:
  System Template: NS_WorkbenchSparks
  Location: Get Actor Location
  Rotation: Get Actor Rotation
  Scale: (1,1,1)
  Auto Destroy: true (auto-destroys when done)
→ Returns: NiagaraComponent reference
```

### Spawn Attached to a Component
```
Spawn System Attached:
  System Template: NS_SaberGlow
  Attach To Component: GetMesh
  Attach Point Name: "SaberTip" (socket name)
  Location/Rotation Type: Snap to Target
  → Returns: NiagaraComponent
```

### Control at Runtime
```
Get NiagaraComponentRef →
  Activate (true = play from start)
  Deactivate (stop immediately)
  Set Niagara Variable (Bool/Float/Vector/Actor): override parameters at runtime
```

### Dynamic Parameters
```
In Niagara: Add Dynamic Material Parameter module
In Blueprint:
  DynMatRef → Set Scalar Parameter Value ("GlowIntensity", 5.0)
  NiagaraComp → Set Niagara Variable Float ("User.Speed", CurrentSpeed)
```

---

## 7. Performance Guidelines

| Particle Count | Target | Notes |
|----------------|--------|-------|
| CPU sim | < 10,000 | Per emitter |
| GPU sim | < 1,000,000 | Must use Fixed Bounds |
| Light renderer | < 50 | Very expensive |
| Ribbon renderer | < 500 | Per emitter |

### Optimization Techniques
1. **Fixed Bounds** — GPU sim REQUIRES this; prevents CPU culling calculations
2. **LOD Distances** — Add Niagara LODs for distance-based simplification
3. **Cull large effects** — Niagara System Scalability settings
4. **Reuse particles** — Use `Set Niagara Variable` to reset instead of re-spawning
5. **Minimize Sub UV** — large SubUV sheets consume texture memory
6. **Avoid Particle Color per-frame changes** — expensive with many particles
7. **Prefer GPU for visual effects** — only use CPU when you need collision/events
