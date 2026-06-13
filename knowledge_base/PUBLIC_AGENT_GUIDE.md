# Public Agent Guide

Use this guide as the safe default context for MCP clients.

## Workflow

1. Confirm Unreal Editor is open and the UnrealMCP plugin is listening on `127.0.0.1:55557`.
2. Use MCP tools for editor actions instead of guessing asset paths or graph structure.
3. Inspect before mutating: list actors, list assets, read Blueprint graphs, then make changes.
4. Keep project-specific assumptions in local private notes, not in this public repository.
5. Return structured evidence: asset paths created, compile results, validation output, and screenshots when relevant.

## Public Safety Rules

- Never expose private project names, asset lists, credentials, or local machine paths in committed docs.
- Do not paste raw PDFs, full chapters, or local-only book paths into tracked files.
- Use generic examples such as `/Game/MyProject/...`.
- Prefer environment variables for host, port, and secret configuration.

## Useful Topics

- `overview` - public repo and privacy rules.
- `agent` - safe MCP agent workflow.
- `tools` - high-level MCP tool usage overview.
