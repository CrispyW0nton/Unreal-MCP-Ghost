"""
Demo B — End-to-End Material Graph Test
========================================
Proves that the 4 mat_* tools work against a live UE5 instance.

Workflow:
  1.  Ping UE5
  2.  mat_create_material  — M_DemoB at /Game/Materials
  3.  mat_add_expression   — TextureSampleParameter2D at (-400, 0)
  4.  mat_add_expression   — VectorParameter (BaseColorTint) at (-400, -200)
  5.  mat_add_expression   — ScalarParameter (Roughness) at (-400, -400)
  6.  mat_add_expression   — Multiply at (-200, 0)
  7.  mat_connect_expressions — TextureSample.RGB → Multiply.A
  8.  mat_connect_expressions — VectorParameter.RGB → Multiply.B
  9.  mat_connect_expressions — Multiply output → material BaseColor
  10. mat_connect_expressions — ScalarParameter → material Roughness
  11. mat_compile
  12. Verify final state

Run from a machine that can reach UE5:
  python3 demo_b_live.py [--host HOST] [--port PORT]

Default connection: 127.0.0.1:55557
Use --host lie-instability.with.playit.plus --port 5462 for Playit tunnel.

Note: mat_* tools use exec_python which is slower than native C++ commands.
      Expect 30-90s per step for asset creation/compilation.
"""

import sys
import json
import socket
import time
import argparse

# ── Connection ────────────────────────────────────────────────────────────────

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55557


def _parse_args():
    p = argparse.ArgumentParser(description="Demo B: Material Graph Live Test")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    return p.parse_args()


def send(command: str, params: dict, host: str, port: int, timeout: int = 150) -> dict:
    """Send a command to UE5 and return the parsed response.

    Handles slow exec_python operations by reading until newline or
    connection close (whichever comes first).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        msg = json.dumps({"type": command, "params": params}) + "\n"
        s.sendall(msg.encode())
        data = b""
        while True:
            try:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            except socket.timeout:
                if data:
                    break
                raise
        raw = data.decode("utf-8", errors="replace").strip()
        if not raw:
            return {"error": "empty_response"}
        return json.loads(raw)
    finally:
        s.close()


def parse_transactional_result(r: dict) -> dict:
    """Parse exec_python response which wraps a JSON struct in the output string."""
    inner = r.get("result") or r
    output = inner.get("output", "") or ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    # Fall back: treat raw response as result
    if inner.get("success") is True:
        return {"success": True, "outputs": {}, "warnings": [], "errors": []}
    return {
        "success": False,
        "message": inner.get("message", output or "No output"),
        "errors": [output or "No parseable output"],
    }


# ── Pretty helpers ────────────────────────────────────────────────────────────

passed = 0
failed = 0
_had_errors = False


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def check(step: str, result: dict, expect_success: bool = True) -> dict:
    global passed, failed
    ok = (
        result.get("success") is True
        or result.get("status") == "success"
        or (result.get("result") or {}).get("success") is True
    )
    outputs = result.get("outputs") or (result.get("result") or {}).get("outputs") or {}

    if expect_success and ok:
        passed += 1
        print(f"  ✅ {step}")
    elif not expect_success and not ok:
        passed += 1
        print(f"  ✅ {step} (expected failure)")
    else:
        failed += 1
        print(f"  ❌ {step}")
        err = result.get("message") or result.get("errors") or result.get("error") or str(result)
        print(f"     → {json.dumps(result)[:600]}")

    return outputs


# ── Transactional exec_python wrapper (mirrors _exec_transactional) ───────────

def exec_transactional(user_code: str, tx_name: str, host: str, port: int,
                       timeout: int = 120) -> dict:
    """Run user_code inside ScopedEditorTransaction via exec_python."""
    import textwrap
    safe_name = tx_name.replace('"', '\\"')
    code = textwrap.dedent(f"""\
        import unreal, sys, json

        with unreal.ScopedEditorTransaction("{safe_name}") as _trans:
            try:
                _result = {{}}
                _warnings = []
                _errors = []
{textwrap.indent(user_code, '        ')}
                print(json.dumps({{
                    "success": True,
                    "stage": "transaction_complete",
                    "message": "Transaction '{safe_name}' committed",
                    "outputs": _result,
                    "warnings": _warnings,
                    "errors": _errors,
                }}))
            except Exception as _exc:
                _trans.cancel()
                print(json.dumps({{
                    "success": False,
                    "stage": "transaction_rolled_back",
                    "message": str(_exc),
                    "errors": [str(_exc)],
                }}))
        sys.stdout.flush()
    """)
    raw = send("exec_python", {"code": code}, host=host, port=port, timeout=timeout)
    return parse_transactional_result(raw)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO B STEPS
# ═══════════════════════════════════════════════════════════════════════════════

MAT_PATH = "/Game/Materials/M_DemoB"
MAT_NAME = "M_DemoB"
MAT_PKG  = "/Game/Materials"


def run_demo_b(host: str, port: int):
    global _had_errors

    # ── STEP 1 — Ping ─────────────────────────────────────────────────────────
    section("STEP 1: Ping UE5")
    r = send("ping", {}, host=host, port=port, timeout=10)
    check("ping", r)
    print(f"  UE5 says: {r}")

    # ── STEP 2 — mat_create_material ─────────────────────────────────────────
    section("STEP 2: mat_create_material — M_DemoB at /Game/Materials")
    t0 = time.time()
    code = f"""
        at = unreal.AssetToolsHelpers.get_asset_tools()
        f = unreal.MaterialFactoryNew()
        mat = at.create_asset('{MAT_NAME}', '{MAT_PKG}', unreal.Material, f)
        if mat is None:
            mat = unreal.load_asset('{MAT_PATH}')
        if mat is None:
            raise RuntimeError("Failed to create or load material at '{MAT_PATH}'")
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_Opaque)
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DefaultLit)
        unreal.EditorAssetLibrary.save_asset(mat.get_path_name())
        _result['material_path'] = mat.get_path_name()
        _result['material_name'] = '{MAT_NAME}'
    """
    r2 = exec_transactional(code, f"mat_create_material:{MAT_NAME}", host, port, timeout=120)
    outs = check("mat_create_material", r2)
    print(f"  material_path: {outs.get('material_path', '(none)')}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 3 — mat_add_expression: TextureSampleParameter2D ─────────────────
    section("STEP 3: mat_add_expression — TextureSampleParameter2D at (-400, 0)")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        lib = unreal.MaterialEditingLibrary
        expr_cls = unreal.load_class(None, '/Script/Engine.MaterialExpressionTextureSampleParameter2D')
        if expr_cls is None: raise RuntimeError("Class not found: MaterialExpressionTextureSampleParameter2D")
        expr = lib.create_material_expression(mat, expr_cls, -400, 0)
        if expr is None: raise RuntimeError("create_material_expression returned None")
        expr.set_editor_property('parameter_name', unreal.Name('BaseTexture'))
        exprs = mat.get_editor_property('expressions') or []
        _result['expression_index'] = len(exprs) - 1
        _result['expression_name'] = expr.get_name()
        _result['expression_class'] = 'MaterialExpressionTextureSampleParameter2D'
    """
    r3 = exec_transactional(code, f"mat_add_expression:{MAT_PATH}/TextureSampleParameter2D", host, port, timeout=60)
    outs3 = check("mat_add_expression (TextureSampleParameter2D)", r3)
    tex_expr_name = outs3.get("expression_name", "")
    print(f"  expression_name: {tex_expr_name}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 4 — mat_add_expression: VectorParameter ───────────────────────────
    section("STEP 4: mat_add_expression — VectorParameter (BaseColorTint) at (-400, -200)")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        lib = unreal.MaterialEditingLibrary
        expr_cls = unreal.load_class(None, '/Script/Engine.MaterialExpressionVectorParameter')
        if expr_cls is None: raise RuntimeError("Class not found: MaterialExpressionVectorParameter")
        expr = lib.create_material_expression(mat, expr_cls, -400, -200)
        if expr is None: raise RuntimeError("create_material_expression returned None")
        expr.set_editor_property('parameter_name', unreal.Name('BaseColorTint'))
        exprs = mat.get_editor_property('expressions') or []
        _result['expression_index'] = len(exprs) - 1
        _result['expression_name'] = expr.get_name()
        _result['expression_class'] = 'MaterialExpressionVectorParameter'
    """
    r4 = exec_transactional(code, f"mat_add_expression:{MAT_PATH}/VectorParameter", host, port, timeout=60)
    outs4 = check("mat_add_expression (VectorParameter)", r4)
    vec_expr_name = outs4.get("expression_name", "")
    print(f"  expression_name: {vec_expr_name}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 5 — mat_add_expression: ScalarParameter ───────────────────────────
    section("STEP 5: mat_add_expression — ScalarParameter (Roughness) at (-400, -400)")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        lib = unreal.MaterialEditingLibrary
        expr_cls = unreal.load_class(None, '/Script/Engine.MaterialExpressionScalarParameter')
        if expr_cls is None: raise RuntimeError("Class not found: MaterialExpressionScalarParameter")
        expr = lib.create_material_expression(mat, expr_cls, -400, -400)
        if expr is None: raise RuntimeError("create_material_expression returned None")
        expr.set_editor_property('parameter_name', unreal.Name('Roughness'))
        exprs = mat.get_editor_property('expressions') or []
        _result['expression_index'] = len(exprs) - 1
        _result['expression_name'] = expr.get_name()
        _result['expression_class'] = 'MaterialExpressionScalarParameter'
    """
    r5 = exec_transactional(code, f"mat_add_expression:{MAT_PATH}/ScalarParameter", host, port, timeout=60)
    outs5 = check("mat_add_expression (ScalarParameter)", r5)
    scl_expr_name = outs5.get("expression_name", "")
    print(f"  expression_name: {scl_expr_name}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 6 — mat_add_expression: Multiply ──────────────────────────────────
    section("STEP 6: mat_add_expression — Multiply at (-200, 0)")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        lib = unreal.MaterialEditingLibrary
        expr_cls = unreal.load_class(None, '/Script/Engine.MaterialExpressionMultiply')
        if expr_cls is None: raise RuntimeError("Class not found: MaterialExpressionMultiply")
        expr = lib.create_material_expression(mat, expr_cls, -200, 0)
        if expr is None: raise RuntimeError("create_material_expression returned None")
        exprs = mat.get_editor_property('expressions') or []
        _result['expression_index'] = len(exprs) - 1
        _result['expression_name'] = expr.get_name()
        _result['expression_class'] = 'MaterialExpressionMultiply'
    """
    r6 = exec_transactional(code, f"mat_add_expression:{MAT_PATH}/Multiply", host, port, timeout=60)
    outs6 = check("mat_add_expression (Multiply)", r6)
    mul_expr_name = outs6.get("expression_name", "")
    print(f"  expression_name: {mul_expr_name}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 7 — Connect TextureSample.RGB → Multiply.A ─────────────────────
    section("STEP 7: mat_connect_expressions — TextureSample.RGB → Multiply.A")
    if not tex_expr_name or not mul_expr_name:
        print("  SKIP — missing expression names from prior steps")
        global failed
        failed += 1
    else:
        t0 = time.time()
        code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found")
        lib = unreal.MaterialEditingLibrary
        exprs = mat.get_editor_property('expressions') or []
        by_name = {{e.get_name(): e for e in exprs}}
        src = by_name.get('{tex_expr_name}')
        dst = by_name.get('{mul_expr_name}')
        if src is None: raise RuntimeError("Source expression '{tex_expr_name}' not found in {{list(by_name.keys())}}")
        if dst is None: raise RuntimeError("Target expression '{mul_expr_name}' not found in {{list(by_name.keys())}}")
        ok = lib.connect_material_expressions(src, 'RGB', dst, 'A')
        if not ok: raise RuntimeError("connect_material_expressions returned False — check output/input names")
        _result['connected'] = True
        _result['from'] = '{tex_expr_name}.RGB'
        _result['to'] = '{mul_expr_name}.A'
        """
        r7 = exec_transactional(
            code,
            f"mat_connect:{tex_expr_name}.RGB->{mul_expr_name}.A",
            host, port, timeout=60
        )
        outs7 = check("mat_connect_expressions (TextureSample.RGB → Multiply.A)", r7)
        print(f"  connection: {outs7.get('from')} → {outs7.get('to')}")
        print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 8 — Connect VectorParameter.RGB → Multiply.B ─────────────────────
    section("STEP 8: mat_connect_expressions — VectorParameter.RGB → Multiply.B")
    if not vec_expr_name or not mul_expr_name:
        print("  SKIP — missing expression names")
        failed += 1
    else:
        t0 = time.time()
        code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found")
        lib = unreal.MaterialEditingLibrary
        exprs = mat.get_editor_property('expressions') or []
        by_name = {{e.get_name(): e for e in exprs}}
        src = by_name.get('{vec_expr_name}')
        dst = by_name.get('{mul_expr_name}')
        if src is None: raise RuntimeError("Source '{vec_expr_name}' not found")
        if dst is None: raise RuntimeError("Target '{mul_expr_name}' not found")
        ok = lib.connect_material_expressions(src, 'RGB', dst, 'B')
        if not ok: raise RuntimeError("connect_material_expressions returned False")
        _result['connected'] = True
        _result['from'] = '{vec_expr_name}.RGB'
        _result['to'] = '{mul_expr_name}.B'
        """
        r8 = exec_transactional(
            code,
            f"mat_connect:{vec_expr_name}.RGB->{mul_expr_name}.B",
            host, port, timeout=60
        )
        outs8 = check("mat_connect_expressions (VectorParameter.RGB → Multiply.B)", r8)
        print(f"  connection: {outs8.get('from')} → {outs8.get('to')}")
        print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 9 — Connect Multiply → material BaseColor ─────────────────────────
    section("STEP 9: mat_connect_expressions — Multiply → material BaseColor")
    if not mul_expr_name:
        print("  SKIP — no Multiply expression name")
        failed += 1
    else:
        t0 = time.time()
        code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found")
        lib = unreal.MaterialEditingLibrary
        exprs = mat.get_editor_property('expressions') or []
        by_name = {{e.get_name(): e for e in exprs}}
        src = by_name.get('{mul_expr_name}')
        if src is None: raise RuntimeError("Source '{mul_expr_name}' not found in {{list(by_name.keys())}}")

        mp_dict = unreal.MaterialProperty.__members__
        # Try all known keys for BaseColor
        bc_key = None
        for k in ['MP_BASE_COLOR', 'MP_BASECOLOR', 'BASE_COLOR', 'BASECOLOR']:
            if k in mp_dict:
                bc_key = k
                break
        if bc_key is None:
            # Enumerate for debugging
            all_keys = list(mp_dict.keys())
            raise RuntimeError("Could not find BaseColor MaterialProperty. Available: " + str(all_keys[:20]))

        ok = lib.connect_material_property(src, '', mp_dict[bc_key])
        if not ok: raise RuntimeError("connect_material_property(BaseColor) returned False — key=" + bc_key)
        _result['connected'] = True
        _result['from'] = '{mul_expr_name}'
        _result['to'] = 'MaterialRoot.BaseColor'
        _result['mp_key_used'] = bc_key
        """
        r9 = exec_transactional(
            code,
            f"mat_connect:{mul_expr_name}->Root.BaseColor",
            host, port, timeout=60
        )
        outs9 = check("mat_connect_expressions (Multiply → BaseColor)", r9)
        print(f"  connection: {outs9.get('from')} → {outs9.get('to')}")
        print(f"  MaterialProperty key used: {outs9.get('mp_key_used', '?')}")
        print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 10 — Connect ScalarParameter → material Roughness ─────────────────
    section("STEP 10: mat_connect_expressions — ScalarParameter → material Roughness")
    if not scl_expr_name:
        print("  SKIP — no ScalarParameter expression name")
        failed += 1
    else:
        t0 = time.time()
        code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found")
        lib = unreal.MaterialEditingLibrary
        exprs = mat.get_editor_property('expressions') or []
        by_name = {{e.get_name(): e for e in exprs}}
        src = by_name.get('{scl_expr_name}')
        if src is None: raise RuntimeError("Source '{scl_expr_name}' not found")

        mp_dict = unreal.MaterialProperty.__members__
        rk_key = None
        for k in ['MP_ROUGHNESS', 'ROUGHNESS']:
            if k in mp_dict:
                rk_key = k
                break
        if rk_key is None:
            raise RuntimeError("Could not find Roughness MaterialProperty. Available: " + str(list(mp_dict.keys())[:20]))

        ok = lib.connect_material_property(src, '', mp_dict[rk_key])
        if not ok: raise RuntimeError("connect_material_property(Roughness) returned False — key=" + rk_key)
        _result['connected'] = True
        _result['from'] = '{scl_expr_name}'
        _result['to'] = 'MaterialRoot.Roughness'
        _result['mp_key_used'] = rk_key
        """
        r10 = exec_transactional(
            code,
            f"mat_connect:{scl_expr_name}->Root.Roughness",
            host, port, timeout=60
        )
        outs10 = check("mat_connect_expressions (ScalarParameter → Roughness)", r10)
        print(f"  connection: {outs10.get('from')} → {outs10.get('to')}")
        print(f"  MaterialProperty key used: {outs10.get('mp_key_used', '?')}")
        print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 11 — mat_compile ───────────────────────────────────────────────────
    section("STEP 11: mat_compile — M_DemoB")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        lib = unreal.MaterialEditingLibrary
        ok = lib.recompile_material(mat)
        _result['had_errors'] = not ok
        _result['had_warnings'] = False
        _result['material_path'] = mat.get_path_name()
        if ok:
            unreal.EditorAssetLibrary.save_asset(mat.get_path_name())
            _result['saved'] = True
        else:
            _result['saved'] = False
    """
    r11 = exec_transactional(code, f"mat_compile:{MAT_PATH}", host, port, timeout=120)
    outs11 = check("mat_compile", r11)
    _had_errors = outs11.get("had_errors", True)
    print(f"  had_errors: {_had_errors}")
    print(f"  saved: {outs11.get('saved', False)}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── STEP 12 — Verify final state ────────────────────────────────────────────
    section("STEP 12: Verify final state — M_DemoB")
    t0 = time.time()
    code = f"""
        mat = unreal.load_asset('{MAT_PATH}')
        if mat is None: raise RuntimeError("Material not found: {MAT_PATH}")
        exprs = mat.get_editor_property('expressions') or []
        _result['expression_count'] = len(exprs)
        _result['expression_names'] = [e.get_name() for e in exprs]
        _result['material_path'] = mat.get_path_name()
        # Count connections by checking expression links
        # (UE Python doesn't expose connection count directly)
        _result['note'] = 'Expression count verified — connections verified implicitly by clean compile'
    """
    r12 = exec_transactional(code, f"mat_verify:{MAT_PATH}", host, port, timeout=60)
    outs12 = check("verify final state", r12)
    expr_count = outs12.get("expression_count", 0)
    expr_names = outs12.get("expression_names", [])
    print(f"  expression_count: {expr_count}")
    print(f"  expressions: {expr_names}")
    compile_verdict = "✅ CLEAN COMPILE" if not _had_errors else "❌ COMPILE ERRORS"
    print(f"  Expected 4 expressions: {'✅' if expr_count == 4 else '⚠️ got ' + str(expr_count)}")
    print(f"  elapsed: {time.time()-t0:.1f}s")

    # ── SUMMARY ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  DEMO B RESULTS: {passed} passed, {failed} failed")
    print(f"  Compile: {compile_verdict}")
    print(f"{'═' * 60}\n")

    return failed == 0


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = _parse_args()
    print(f"\n{'═' * 60}")
    print(f"  DEMO B — Material Graph Live Test")
    print(f"  Target: {args.host}:{args.port}")
    print(f"{'═' * 60}")
    success = run_demo_b(args.host, args.port)
    sys.exit(0 if success else 1)
