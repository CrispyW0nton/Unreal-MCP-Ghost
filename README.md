# Unreal-MCP-Ghost

Unreal-MCP-Ghost lets MCP-capable AI clients control Unreal Engine 5 through a local Python MCP server and a UE editor plugin. It is intended for developers who want repeatable AI-assisted editor automation for Blueprint authoring, level inspection, actor spawning, UMG work, asset setup, diagnostics, and related UE workflows.

`main` is the stable public branch. Experimental work belongs on `wip`.

## What Is Included

- `unreal_plugin/` - Unreal Engine editor plugin source.
- `unreal_mcp_server/` - Python MCP server and tool wrappers.
- `skills/` - Higher-level workflow skills built on top of MCP tools.
- `cursor_setup/` and `cursor_mcp_config.json` - Generic local client setup examples.
- `knowledge_base/` - Reusable MCP and Unreal guidance, including curated book-derived knowledge files used by agents.

## What Is Not Included

This repository intentionally does not ship private Unreal projects, generated game assets, raw PDFs, local-only book paths, or per-client secrets. Keep those in your own project workspace or in ignored local knowledge-base folders.

Ignored private locations include:

- `knowledge_base/Projects/`
- `knowledge_base/private/`
- `docs/knowledge-base/local-book-paths.json`
- `local-book-paths.json`

## Requirements

- Unreal Engine 5.4 or newer.
- Visual Studio 2022 with the "Game development with C++" workload.
- Python 3.10 or newer.
- An MCP client such as Cursor, Claude Desktop, or another compatible client.

## Quick Start

Clone the stable branch:

```powershell
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git
cd Unreal-MCP-Ghost
git checkout main
```

Install Python dependencies:

```powershell
python -m pip install -e .
```

Copy the Unreal plugin into your project:

```powershell
$Repo = "C:\Dev\Unreal-MCP-Ghost"
$Project = "C:\Users\YourName\Documents\UnrealProjects\MyGame"

New-Item -ItemType Directory -Force -Path "$Project\Plugins\UnrealMCP"
Copy-Item -Recurse -Force "$Repo\unreal_plugin\*" "$Project\Plugins\UnrealMCP\"
```

Regenerate Visual Studio project files for your `.uproject`, build the project in `Development Editor | Win64`, then open the Unreal Editor. The plugin should listen on `127.0.0.1:55557` when loaded.

Start the MCP server:

```powershell
python unreal_mcp_server\unreal_mcp_server.py
```

Configure your MCP client with a command like:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "python",
      "args": ["C:/Dev/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py"],
      "env": {
        "UNREAL_HOST": "127.0.0.1",
        "UNREAL_PORT": "55557"
      }
    }
  }
}
```

Restart the client after changing MCP configuration.

## Development Branches

- `main` - stable public branch.
- `wip` - experimental branch for active feature work.

Do not publish private project folders, generated media, raw PDF files, API keys, or Unreal project assets to `main`.

## Legal

Unreal-MCP-Ghost is distributed under the GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).

Portions of this project are derived from or inspired by the original `chongdashu/unreal-mcp` project. See [NOTICE.md](NOTICE.md) for attribution and license notes.

The AGPL is intended to preserve user freedom and discourage closed-source appropriation of this codebase. It is not a substitute for legal advice; consult counsel before relying on it for commercial enforcement.

## Security

Report security issues privately using the guidance in [SECURITY.md](SECURITY.md). Do not open public issues for vulnerabilities, secrets, or exploit details.
