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
- Git.
- An MCP client such as Cursor, Claude Desktop, or another compatible client.

## User Guide

This guide covers the normal first-time path:

1. Install Unreal-MCP-Ghost.
2. Add your game project context to the local knowledge base.
3. Work with an AI agent effectively while building a game.

## 1. Install

Clone the stable branch:

```powershell
git clone https://github.com/CrispyW0nton/Unreal-MCP-Ghost.git C:\Dev\Unreal-MCP-Ghost
cd C:\Dev\Unreal-MCP-Ghost
git checkout main
```

Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Copy the Unreal plugin into your Unreal project:

```powershell
$Repo = "C:\Dev\Unreal-MCP-Ghost"
$Project = "C:\Users\YourName\Documents\UnrealProjects\MyGame"

New-Item -ItemType Directory -Force -Path "$Project\Plugins\UnrealMCP"
Copy-Item -Recurse -Force "$Repo\unreal_plugin\*" "$Project\Plugins\UnrealMCP\"
```

Regenerate project files and build:

1. Right-click your `.uproject`.
2. Select `Generate Visual Studio project files`.
3. Open the generated `.sln`.
4. Build `Development Editor | Win64`.
5. Open the Unreal project.

Confirm the plugin is running:

- In Unreal Editor, open `Edit > Plugins` and verify `UnrealMCP` is enabled.
- In the Output Log, look for the plugin listening on `127.0.0.1:55557`.

Start the MCP server:

```powershell
cd C:\Dev\Unreal-MCP-Ghost
.\.venv\Scripts\Activate.ps1
python unreal_mcp_server\unreal_mcp_server.py
```

Configure your MCP client. For Cursor or another stdio MCP client, use a config like:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "C:/Dev/Unreal-MCP-Ghost/.venv/Scripts/python.exe",
      "args": ["C:/Dev/Unreal-MCP-Ghost/unreal_mcp_server/unreal_mcp_server.py"],
      "env": {
        "UNREAL_HOST": "127.0.0.1",
        "UNREAL_PORT": "55557"
      }
    }
  }
}
```

Restart your MCP client after changing its config.

Run a smoke test in your AI client:

```text
List the actors in the current Unreal level. If Unreal is not reachable, tell me exactly what connection step failed.
```

If the tool is wired correctly, the agent should call an Unreal-MCP tool and return level data.

## 2. Set Up Your Project In The Knowledge Base

Agents work best when they know your project rules, asset paths, gameplay goals, and current state. Put that context in `knowledge_base/Projects/`, which is ignored by git so your private game details do not ship in the public repo.

Create a project folder:

```powershell
New-Item -ItemType Directory -Force -Path knowledge_base\Projects\MyGame
```

Create `knowledge_base/Projects/MyGame/PROJECT_CONTEXT.md`:

```markdown
# MyGame Project Context

## Engine

- Unreal version: 5.4/5.5/5.6
- Project path: C:\Users\YourName\Documents\UnrealProjects\MyGame
- Content root: /Game/MyGame

## Game Vision

Describe the game in 3-5 sentences. Include genre, camera, player fantasy, and the target slice you are building first.

## Current Milestone

Describe what "done" means for the current week or prototype.

## Existing Assets

- Player pawn:
- Game mode:
- Player controller:
- Main level:
- Key UI widgets:
- Important folders:

## Naming Rules

- Blueprints: BP_
- Widgets: WBP_
- Interfaces: BPI_
- Input actions: IA_
- Input mapping contexts: IMC_
- Materials: M_ or MI_

## Agent Rules

- Inspect assets before changing them.
- Prefer small verified changes over large blind rewrites.
- Compile affected Blueprints after editing them.
- Save only assets touched by the requested task.
- Report exact asset paths, compile errors, and follow-up risks.

## Current Task Backlog

1. First task
2. Second task
3. Third task
```

Optional but useful files:

- `knowledge_base/Projects/MyGame/ASSET_MAP.md` - important asset paths and folder layout.
- `knowledge_base/Projects/MyGame/ROADMAP.md` - milestone plan.
- `knowledge_base/Projects/MyGame/BUGS.md` - known broken assets and reproduction steps.
- `knowledge_base/Projects/MyGame/STYLE_GUIDE.md` - naming, folder, UI, and gameplay conventions.
- `knowledge_base/Projects/MyGame/SESSION_LOG.md` - what changed each work session.

Start each agent session by pointing the agent at your private context:

```text
Before editing Unreal, read:
- knowledge_base/00_AGENT_KNOWLEDGE_BASE.md
- knowledge_base/12_MCP_TOOL_USAGE_GUIDE.md
- knowledge_base/Projects/MyGame/PROJECT_CONTEXT.md
- knowledge_base/Projects/MyGame/ASSET_MAP.md if it exists

Then inspect the current Unreal level and summarize what you can safely work on.
```

Keep project context current. When an agent creates or changes important assets, ask it to update your local `ASSET_MAP.md` or `SESSION_LOG.md`.

## 3. Work Effectively On A Game With This Tool

Unreal-MCP-Ghost is strongest when you use it as a disciplined development loop, not as a one-shot "make my game" button.

### The Recommended Loop

1. **Choose one small feature.**
   Good: "Create a health component and show health on the HUD."
   Risky: "Build the whole combat system."

2. **Ask the agent to inspect first.**
   The agent should list relevant Blueprints, components, graphs, widgets, and assets before changing anything.

3. **Ask for a short implementation plan.**
   Require exact assets to be touched and how success will be verified.

4. **Let the agent implement one slice.**
   Prefer one Blueprint, one widget, one mechanic, or one level pass at a time.

5. **Compile, validate, and report.**
   The agent should compile affected Blueprints, run available diagnostics, and report any remaining manual steps.

6. **Test in PIE.**
   Play the game yourself. Keep notes on what worked, what broke, and what should be next.

7. **Update project context.**
   Add new asset paths, decisions, and known issues to your ignored project knowledge base.

### Good Prompts

```text
Read my project context, inspect the current level, then create a plan for a simple interactable door. Do not edit anything until you list the assets you intend to touch.
```

```text
Implement only the health component slice: create or update the component, add variables, expose clear functions, compile it, and report exact asset paths.
```

```text
Audit BP_PlayerCharacter and WBP_HUD for health display wiring. Inspect first, then tell me what is missing before making changes.
```

```text
Create a SESSION_LOG entry summarizing what changed today, what compiled, what failed, and the next safest task.
```

### Habits That Keep The Project Healthy

- Keep tasks small and testable.
- Prefer existing project patterns over new architecture.
- Ask the agent to inspect before mutation.
- Ask for exact asset paths in every report.
- Compile after Blueprint edits.
- Save intentionally.
- Keep private project notes in `knowledge_base/Projects/`.
- Commit stable progress to your game repo separately from this tool repo.

### What To Avoid

- Do not ask the agent to rewrite many unrelated systems at once.
- Do not let private project notes, generated assets, secrets, or raw PDFs into `main`.
- Do not trust a claimed asset path unless the agent inspected or created it.
- Do not skip PIE testing just because a Blueprint compiled.
- Do not expose your MCP server to the public internet unless you understand the security risks.

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
