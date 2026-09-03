# MCP Tooling Overview

Unreal-MCP-Ghost exposes Unreal Editor workflows through a Python MCP server that forwards structured commands to the Unreal editor plugin.

## Common Flow

1. Start Unreal Editor with the plugin installed in your project.
2. Start `unreal_mcp_server/unreal_mcp_server.py`.
3. Connect an MCP client using stdio or another supported transport.
4. Ask the agent to inspect existing editor state before creating or changing assets.

## Safe Command Pattern

- Read state first.
- Make the smallest useful change.
- Compile or validate affected Blueprints when applicable.
- Report exact asset paths and errors.

## Private Knowledge

Project-specific recipes can be useful, but keep them in ignored local folders such as `knowledge_base/Projects/`.
