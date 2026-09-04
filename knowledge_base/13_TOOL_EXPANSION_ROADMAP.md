# Unreal-MCP-Ghost Public Roadmap

Last updated: 2026-09-03

This roadmap covers reusable Unreal-MCP-Ghost platform work. Project-specific plans,
validation logs, generated reports, and private production context are intentionally
kept outside the public repository.

## North Star

Unreal-MCP-Ghost should let an AI agent inspect, author, validate, and repair Unreal
Engine 5 projects while preserving editor stability, project integrity, and a clear
audit trail.

## Current Surface

- 713 registered MCP tools across 51 categorized modules.
- Unreal Engine 5.6 editor plugin with a localhost TCP bridge on port `55655`.
- Python FastMCP transports for `stdio`, SSE, and streamable HTTP.
- Optional dockable editor chat and IDE cockpit workflows.
- 382 discovered native C++ bridge commands with Python-route coverage auditing.
- Offline inventory, test-lane, wrapper-coverage, and no-mutation validation.

## Operating Rules

- Keep public tools and documentation project-agnostic.
- Keep project knowledge, generated reports, credentials, media, and build output local.
- Prefer read-only discovery before editor mutation.
- Keep each mutation transaction-sized and immediately inspectable.
- Require compile/readback evidence after Blueprint or native authoring changes.
- Keep tool registration, documentation, tests, and inventory counts synchronized.
- Treat paid generation and destructive editor actions as explicit guarded workflows.

## Workstream 0 — Registry and Documentation Hygiene

Status: active maintenance.

- Maintain one canonical static tool inventory.
- Require every registered tool to have a useful docstring and stable schema.
- Keep module categories and roadmap phases machine-readable.
- Detect Python/native bridge route drift in offline CI.
- Keep setup examples portable and free of machine-specific paths.
- Keep generated artifacts and project-only material out of Git.

Definition of done:

- Inventory and documented counts agree.
- No uncategorized public tool modules.
- No tracked build packages, logs, caches, credentials, or private project material.
- Public setup and security guidance matches runtime defaults.

## Workstream 1 — Native Unreal Authoring

Status: ongoing.

- Expand safe Blueprint graph, UMG, Niagara, animation, Control Rig, AI, navigation,
  networking, material, Sequencer, and asset authoring primitives.
- Prefer native bridge routes where editor APIs provide stronger validation or
  transaction support than Python reflection.
- Preserve structured errors and readback for unsupported engine-version paths.

Definition of done:

- Each new native route has a Python wrapper or is explicitly classified as internal.
- Wrapper schema, native routing, and error behavior have offline coverage.
- Live-editor validation is recorded outside the public repository when it contains
  project-specific context.

## Workstream 2 — Runtime Reliability and Safety

Status: ongoing.

- Keep bridge authentication consistent across direct clients, scripts, and proxy paths.
- Bind unauthenticated HTTP/chat surfaces to loopback by default.
- Improve timeout, cancellation, health, and process-ownership behavior.
- Continue eliminating blocking calls from async tool paths.
- Maintain no-mutation and test-lane classification for offline validation.

Definition of done:

- Startup failures are structured and actionable.
- Network exposure requires an authenticated tunnel or reverse proxy.
- Offline validation does not mutate tracked files.
- Long-running provider and bridge calls do not block the async server loop.

## Workstream 3 — IDE Companion and Editor Chat

Status: ongoing.

- Refine session-aware chat history, context, queued actions, evidence, and artifacts.
- Improve tool discovery and operation-status visibility.
- Keep the editor panel useful without coupling the native plugin to a specific AI client.
- Preserve explicit confirmation boundaries for risky or paid operations.

Definition of done:

- A session can be started, resumed, inspected, and handed off deterministically.
- Failed operations expose repair context without hiding the original evidence.
- Chat and cockpit routes follow the same loopback and authentication policy as the MCP server.

## Workstream 4 — Spatial and Generative Workflows

Status: guarded expansion.

- Build reusable spatial inspection, room/zone, clearance, and placement planning.
- Keep generation provider configuration isolated from tool orchestration.
- Require dry-run, spend, import, scale, placement, and validation gates.
- Reuse existing project assets before requesting paid generation.

Definition of done:

- Spatial plans are inspectable before mutation.
- Provider calls are asynchronous and credentials never enter logs or Git.
- Generated assets retain provenance and validation metadata.
- Paid and live-editor lanes remain separate from default offline CI.

## Workstream 5 — Distribution and CI

Status: ongoing.

- Keep lockfiles and dependency bounds reproducible.
- Maintain repeatable offline smoke commands and plugin packaging checks.
- Add CI workflows when repository policy defines required checks.
- Continue measuring startup, discovery, and bridge-route health without committing
  generated reports.

## Canonical Validation

```powershell
python scripts\tool_inventory.py --markdown
python scripts\audit_test_lanes.py
python scripts\audit_high_value_wrapper_coverage.py
python scripts\bridge_command_audit.py
python scripts\run_no_mutation_unittest.py
uv lock --check
```

For native plugin changes, also package the plugin against the supported Unreal Engine
version and retain build evidence locally.

## Contribution Checklist

When adding a public tool:

1. Add or update the implementation and stable result schema.
2. Add focused offline tests.
3. Update the module category registry.
4. Update the documented tool count when the inventory changes.
5. Run no-mutation tests and bridge-route audits.
6. Keep project-specific validation evidence outside the public repository.
