"""
Copy modified plugin source files to project Plugins directory via UE5 Python.
Run from sandbox with: python3 copy_plugin_to_project.py
"""
import sys, os, json, base64
sys.path.insert(0, '/home/user/webapp')
import ue5_client as ue

print("=== Copying Plugin Source Files to Project ===")

# Files to copy: (local_path, relative_path_within_plugin)
FILES = [
    (
        '/home/user/webapp/unreal_plugin/Source/UnrealMCP/Private/Commands/UnrealMCPExtendedCommands.cpp',
        'Source/UnrealMCP/Private/Commands/UnrealMCPExtendedCommands.cpp'
    ),
    (
        '/home/user/webapp/unreal_plugin/Source/UnrealMCP/Public/Commands/UnrealMCPExtendedCommands.h',
        'Source/UnrealMCP/Public/Commands/UnrealMCPExtendedCommands.h'
    ),
    (
        '/home/user/webapp/unreal_plugin/Source/UnrealMCP/UnrealMCP.Build.cs',
        'Source/UnrealMCP/UnrealMCP.Build.cs'
    ),
]

for local_path, plugin_rel_path in FILES:
    print(f"\nProcessing: {os.path.basename(local_path)}")
    
    # Read the file from Linux sandbox
    with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Encode as base64 to safely transfer via exec_py
    b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
    plugin_rel_escaped = plugin_rel_path.replace('\\', '/')
    
    code = f"""
import unreal, os, base64

proj_dir = unreal.Paths.project_dir()
plugin_dir = os.path.join(proj_dir, 'Plugins', 'UnrealMCP')
dst_path = os.path.join(plugin_dir, r'{plugin_rel_escaped}'.replace('/', os.sep))
dst_dir = os.path.dirname(dst_path)

b64 = r'''{b64_content}'''
content = base64.b64decode(b64).decode('utf-8')

os.makedirs(dst_dir, exist_ok=True)
with open(dst_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Written:', dst_path)
print('Size:', os.path.getsize(dst_path))
"""
    
    r = ue.exec_py(code)
    result = ue.get_out(r)
    print(result)
    
    if 'error' in r or ('success' in r and not r.get('result', {}).get('success', True)):
        print(f"ERROR copying {local_path}")
        sys.exit(1)

print("\n=== All files copied successfully! ===")
print("Now rebuild the plugin in Unreal Engine:")
print("  1. Close all BT/BB editors")
print("  2. Go to Tools > Refresh Visual Studio / Compile")
print("  OR")
print("  3. Run: LiveCodingConsole to hot-reload")
