# Reference library — study guides (Unreal-MCP-Ghost)

This folder holds **original study notes** that connect published Unreal Engine books to how **this repository** works (MCP tools, C++ plugin commands, Blueprint automation, AI/animation pipelines).

## Copyright and licensing

- The books listed below are **Packt Publishing** titles. Text in this folder is **not** a reproduction of those books; it is paraphrased guidance and cross-references for contributors.
- Keep your own **licensed** copies (print or eBook from Packt or other authorized sellers). Do not commit full PDFs or large excerpts into the repo (see root `.gitignore` for `*.pdf`).
- One of the paths supplied for Sapio’s book referenced an **OceanofPDF**-branded file. That source is commonly unauthorized. Prefer the **official Packt edition** (ISBN **978-1-78883-565-7**, April 2019) for legal access and updates.

## Giving your AI “full book” context (without putting the book in git)

If the goal is for **Cursor / agents to use every detail** from the PDFs while working on this plugin, the compliant pattern is:

1. **Keep licensed PDFs on disk** (paths only in local config — not committed).
2. **Index them with RAG** (chunk + embed) in a **local** vector store or Cursor/IDE feature that reads from your machine.
3. At query time, the agent **retrieves** relevant pages/sections into context. That preserves *information access* for the AI without **redistributing** Packt’s copyrighted expression in the repo.

Duplicating whole chapters or the full text into `docs/` or rules would still be **unauthorized reproduction**, regardless of intent. Paraphrased guides in this folder are safe; **verbatim bulk copy is not**.

### Optional: point the agent at your PDF files (local)

1. Copy `docs/knowledge-base/local-book-paths.example.json` to **`local-book-paths.json`** in the **repo root** (already gitignored).
2. Fix the three `"path"` entries if your files moved.
3. Cursor will use that file **only when following** `.cursor/rules/unreal-mcp-book-knowledge.mdc` — for short reads / retrieval, not for committing book text.

## Index

| Guide | Focus | Relates to this repo |
| --- | --- | --- |
| [unreal-cpp-li-2023.md](unreal-cpp-li-2023.md) | UE5 C++ gameplay, `UPROPERTY` / `UFUNCTION`, AnimInstance, collisions, multiplayer | `unreal_plugin/` C++ commands, gameplay wiring |
| [elevating-game-experiences-ue5-2e.md](elevating-game-experiences-ue5-2e.md) | Editor fluency, Blueprint-first workflows, “experience” quality | MCP Blueprint/UMG tools, iteration discipline |
| [game-ai-unreal-sapio-2019.md](game-ai-unreal-sapio-2019.md) | BTs, navigation, EQS, perception-style AI framing | `build_behavior_tree`, BT/BBC tools, AI-related MCP commands |

## Suggested reading order for MCP contributors

1. **Li (C++)** — understand module boundaries, reflection macros, and where C++ must back MCP operations.
2. **Marques et al. (Elevating experiences)** — align editor habits with safe automation (compile/save/delegate chains in UE5.6).
3. **Sapio (AI)** — map high-level AI architecture to the MCP BT/Blackboard surface.

## Maintenance

When you adopt a new practice from a book, add **original** bullets or checklists to the relevant guide (paraphrase and synthesize). Do **not** paste chapter text or multi-page excerpts.
