# Unreal-MCP-Ghost — Skills Library

Skills are reusable, documented scripting recipes that package a common
Unreal Engine workflow into a form AI agents can follow reliably.

Each skill defines:
- **What it does** (name, description)
- **Which MCP tools it uses** (required_tools)
- **Pre-conditions** (what must exist or be true before the skill runs)
- **Post-conditions** (what the agent can verify after success)
- **Failure modes** (known failure patterns and how to recover)
- **Validation steps** (how to confirm the operation succeeded)
- **Example prompts** (natural-language trigger phrases)

## Skills in this library

| File | Skill | Category |
|---|---|---|
| [SKILL_import_texture.md](SKILL_import_texture.md) | Import Texture | Asset Import |
| [SKILL_import_static_mesh.md](SKILL_import_static_mesh.md) | Import Static Mesh | Asset Import |
| [SKILL_import_skeletal_mesh.md](SKILL_import_skeletal_mesh.md) | Import Skeletal Mesh | Asset Import |
| [SKILL_batch_import_folder.md](SKILL_batch_import_folder.md) | Batch Import Folder | Asset Import |
| [SKILL_import_folder_as_character.md](SKILL_import_folder_as_character.md) | Import Folder as Character | Asset Import |
| [SKILL_diagnose_failed_import.md](SKILL_diagnose_failed_import.md) | Diagnose Failed Import | Diagnostics |
| [SKILL_compile_validate_blueprint.md](SKILL_compile_validate_blueprint.md) | Compile & Validate Blueprint | Blueprint |

## Design principles

1. **Use structured execution** — prefer `ue_exec_safe` / `ue_exec_transact`
   over raw `exec_python` for all mutating operations.
2. **Inspect before mutating** — use `ue_describe_asset`, `ue_reflect_class`,
   or `ue_list_editor_selection` to verify the state before changing it.
3. **Check the log after every operation** — call `get_recent_output_log`
   with `filter_category="Error"` after every import or compile.
4. **Return structured summaries** — all skill outputs follow the
   `StructuredResult` schema (`success`, `stage`, `message`, `outputs`,
   `warnings`, `errors`, `log_tail`).
5. **One undo step per logical action** — wrap mutations in `ue_exec_transact`
   so the editor's Undo history stays clean.
