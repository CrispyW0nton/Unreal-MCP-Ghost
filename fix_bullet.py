"""
Fix BP_Bullet:
- Remove all collision (NoCollision on sphere + mesh) so it can't self-destroy
- Make the static mesh bigger so it's visible
- Reapply ProjectileMovement speed (2000 u/s, no gravity)
"""
import sys, json, socket
sys.path.insert(0, '/home/user/webapp')

HOST = "lie-instability.with.playit.plus"
PORT = 5462
TIMEOUT = 30

def send_command(command, params=None):
    msg = json.dumps({"type": command, "params": params or {}}) + "\n"
    s = socket.socket()
    s.settimeout(TIMEOUT)
    s.connect((HOST, PORT))
    s.sendall(msg.encode("utf-8"))
    chunks = []
    while True:
        try:
            chunk = s.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        try:
            return json.loads(data.decode("utf-8").strip())
        except json.JSONDecodeError:
            continue
    s.close()
    return {}

def run(code):
    r = send_command("exec_python", {"code": code})
    print("Response:", json.dumps(r, indent=2))
    return r

# ── 1. NoCollision on all bullet components ────────────────────────────────
print("\n=== Step 1: Set all BP_Bullet components to NoCollision ===")
run(
"import unreal\n"
"updated = []\n"
"for obj in unreal.ObjectIterator(unreal.SphereComponent):\n"
"    p = obj.get_path_name()\n"
"    if 'BP_Bullet' in p and 'TRASH' not in p and 'CollisionSphere' in p:\n"
"        obj.set_collision_profile_name('NoCollision')\n"
"        obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)\n"
"        updated.append('Sphere:' + p.split(':')[-1])\n"
"for obj in unreal.ObjectIterator(unreal.StaticMeshComponent):\n"
"    p = obj.get_path_name()\n"
"    if 'BP_Bullet' in p and 'TRASH' not in p:\n"
"        obj.set_collision_profile_name('NoCollision')\n"
"        obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)\n"
"        try:\n"
"            obj.set_editor_property('relative_scale3d', unreal.Vector(0.3, 0.3, 0.3))\n"
"        except Exception:\n"
"            pass\n"
"        updated.append('Mesh:' + p.split(':')[-1])\n"
"for item in updated:\n"
"    print('[OK]', item)\n"
"print('Total updated:', len(updated))\n"
)

# ── 2. Fix ProjectileMovement speed ───────────────────────────────────────
print("\n=== Step 2: Fix ProjectileMovement speed ===")
run(
"import unreal\n"
"for obj in unreal.ObjectIterator(unreal.ProjectileMovementComponent):\n"
"    p = obj.get_path_name()\n"
"    if 'BP_Bullet' in p and 'TRASH' not in p:\n"
"        obj.set_editor_property('initial_speed', 2000.0)\n"
"        obj.set_editor_property('max_speed', 2000.0)\n"
"        obj.set_editor_property('projectile_gravity_scale', 0.0)\n"
"        obj.set_editor_property('rotation_follows_velocity', True)\n"
"        obj.set_editor_property('should_bounce', False)\n"
"        spd = obj.get_editor_property('initial_speed')\n"
"        print('[PM] speed =', spd, ' path:', p.split(':')[-1])\n"
)

# ── 3. Compile + save ──────────────────────────────────────────────────────
print("\n=== Step 3: Compile and save ===")
run(
"import unreal\n"
"bp = unreal.EditorAssetLibrary.load_asset('/Game/Blueprints/BP_Bullet')\n"
"unreal.BlueprintEditorLibrary.compile_blueprint(bp)\n"
"unreal.EditorAssetLibrary.save_asset('/Game/Blueprints/BP_Bullet', only_if_is_dirty=False)\n"
"print('[DONE] BP_Bullet compiled and saved')\n"
)
