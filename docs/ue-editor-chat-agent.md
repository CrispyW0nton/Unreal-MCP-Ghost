# UE Editor Chat Agent

The Unreal Editor chat panel sends human messages to the MCP HTTP server and polls for agent messages. To make Cursor answer automatically, run the chat agent watcher in a separate terminal.

## Requirements

- MCP server running with HTTP/SSE on port 8000:

```powershell
python unreal_mcp_server\unreal_mcp_server.py --transport sse --mcp-host 127.0.0.1 --mcp-port 8000
```

- `CURSOR_API_KEY` set for the watcher process.

## Start Automatic Replies

```powershell
$env:CURSOR_API_KEY = "cursor_..."
npm run chat:agent
```

Optional environment variables:

- `UE_CHAT_SERVER_URL` — defaults to `http://127.0.0.1:8000`
- `UE_CHAT_POLL_INTERVAL_MS` — defaults to `2000`
- `UE_CHAT_CATCH_UP=1` — respond to existing human messages on startup instead of only new messages
- `UE_CHAT_RUN_ONCE=1` — poll once and exit, useful for smoke tests
- `UE_CHAT_SESSION` — optional named MCP Chat session to poll, read, and answer in isolation
- `CURSOR_MODEL` — defaults to `auto`
- `UE_CHAT_AGENT_CWD` — defaults to the current repo

## How It Works

1. Polls `/chat/poll?sender=human`, scoped to `UE_CHAT_SESSION` when set.
2. Sends each new human message to a local Cursor SDK agent.
3. The local agent loads project MCP config from `.cursor/mcp.json`.
4. Posts the final reply to `/chat/send` with `sender="agent"` and the same optional session.
5. The Unreal Editor chat panel displays the reply on its next poll.
