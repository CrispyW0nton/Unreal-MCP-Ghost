#!/usr/bin/env node

import { Agent } from "@cursor/sdk";

const SERVER_URL = (process.env.UE_CHAT_SERVER_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const POLL_INTERVAL_MS = Number.parseInt(process.env.UE_CHAT_POLL_INTERVAL_MS || "2000", 10);
const MODEL_ID = process.env.CURSOR_MODEL || "auto";
const CWD = process.env.UE_CHAT_AGENT_CWD || process.cwd();
const CATCH_UP = process.env.UE_CHAT_CATCH_UP === "1";
const RUN_ONCE = process.env.UE_CHAT_RUN_ONCE === "1";
const MAX_HISTORY = Number.parseInt(process.env.UE_CHAT_HISTORY_LIMIT || "10", 10);
const CHAT_SESSION = (process.env.UE_CHAT_SESSION || "").trim();

let since = CATCH_UP ? "" : new Date().toISOString();
const processedMessageIds = new Set();

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function endpoint(path) {
  return `${SERVER_URL}${path}`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let body = {};
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { raw: text };
    }
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} from ${url}: ${text}`);
  }

  return body;
}

async function pollHumanMessages() {
  const params = new URLSearchParams({ sender: "human" });
  if (CHAT_SESSION) {
    params.set("session", CHAT_SESSION);
  }
  if (since) {
    params.set("since", since);
  }

  const data = await requestJson(endpoint(`/chat/poll?${params.toString()}`));
  const messages = Array.isArray(data.messages) ? data.messages : [];
  return messages.filter((message) => {
    const id = message.message_id || `${message.timestamp}:${message.message}`;
    if (processedMessageIds.has(id)) {
      return false;
    }
    processedMessageIds.add(id);
    return true;
  });
}

async function getRecentHistory() {
  const params = new URLSearchParams({ limit: String(MAX_HISTORY) });
  if (CHAT_SESSION) {
    params.set("session", CHAT_SESSION);
  }
  const data = await requestJson(endpoint(`/chat/history?${params.toString()}`));
  return Array.isArray(data.messages) ? data.messages : [];
}

async function sendAgentMessage(message, context = {}) {
  return requestJson(endpoint("/chat/send"), {
    method: "POST",
    body: JSON.stringify({
      sender: "agent",
      message,
      timestamp: new Date().toISOString(),
      ...(CHAT_SESSION ? { session: CHAT_SESSION } : {}),
      context,
    }),
  });
}

function formatHistory(messages) {
  if (!messages.length) {
    return "(no prior chat history)";
  }

  return messages
    .map((message) => {
      const sender = message.sender || "unknown";
      const text = message.message || "";
      const timestamp = message.timestamp || "";
      return `[${timestamp}] ${sender}: ${text}`;
    })
    .join("\n");
}

function buildPrompt(message, history) {
  const context = message.context && typeof message.context === "object"
    ? JSON.stringify(message.context, null, 2)
    : "{}";

  return `You are ChatGPT 5.5 running in Cursor for the Unreal-MCP-Ghost workspace.

You are replying to a human who is using the Unreal Editor MCP Chat panel. Keep the chat reply concise and useful.

If the user asks for Unreal, Blueprint, gameplay, animation, Sequencer, Control Rig, or MCP changes:
- Follow the repository rules and knowledge base before modifying anything.
- Use MCP tools when needed to inspect or change Unreal state.
- Do not fabricate asset paths or runtime results.
- If a task requires confirmation, ask a clear question instead of guessing.
- If you make changes, summarize what changed and what was verified.

Recent chat history:
${formatHistory(history)}

Current Unreal editor context:
${context}

Human message:
${message.message}

Return only the text that should be posted back into the Unreal Editor chat panel.`;
}

function extractReply(result) {
  if (!result) {
    return "";
  }
  if (typeof result.result === "string") {
    return result.result.trim();
  }
  if (typeof result.output === "string") {
    return result.output.trim();
  }
  if (typeof result.text === "string") {
    return result.text.trim();
  }
  return JSON.stringify(result, null, 2);
}

async function runCursorAgentForMessage(message) {
  const history = await getRecentHistory();
  const prompt = buildPrompt(message, history);

  const result = await Agent.prompt(prompt, {
    apiKey: process.env.CURSOR_API_KEY,
    model: { id: MODEL_ID },
    local: {
      cwd: CWD,
      settingSources: ["project"],
    },
  });

  const reply = extractReply(result);
  if (!reply) {
    return "I received your message, but the Cursor agent returned an empty response.";
  }
  return reply;
}

async function handleHumanMessage(message) {
  const label = message.message_id || message.timestamp || "(no id)";
  console.log(`[ue-chat-agent] human message ${label}: ${message.message}`);

  if (!process.env.CURSOR_API_KEY) {
    await sendAgentMessage(
      "I received your message, but automatic replies need CURSOR_API_KEY set in the chat agent process.",
      { bridge_error: "missing_cursor_api_key" },
    );
    return;
  }

  try {
    const reply = await runCursorAgentForMessage(message);
    await sendAgentMessage(reply, {
      source: "ue-chat-agent",
      human_message_id: message.message_id || "",
    });
    console.log(`[ue-chat-agent] replied to ${label}`);
  } catch (error) {
    const text = error instanceof Error ? error.message : String(error);
    console.error(`[ue-chat-agent] failed to handle ${label}: ${text}`);
    await sendAgentMessage(
      `I received your message, but the Cursor agent failed to respond automatically: ${text}`,
      {
        source: "ue-chat-agent",
        human_message_id: message.message_id || "",
        bridge_error: "cursor_agent_failed",
      },
    );
  }
}

async function main() {
  console.log(`[ue-chat-agent] server=${SERVER_URL}`);
  console.log(`[ue-chat-agent] cwd=${CWD}`);
  console.log(`[ue-chat-agent] model=${MODEL_ID}`);
  console.log(`[ue-chat-agent] session=${CHAT_SESSION || "(legacy default)"}`);
  console.log(`[ue-chat-agent] initial since=${since || "(catch up from beginning)"}`);

  while (true) {
    try {
      const messages = await pollHumanMessages();
      for (const message of messages) {
        await handleHumanMessage(message);
        if (message.timestamp) {
          since = message.timestamp;
        }
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : String(error);
      console.error(`[ue-chat-agent] poll failed: ${text}`);
    }

    if (RUN_ONCE) {
      console.log("[ue-chat-agent] run-once complete");
      return;
    }

    await sleep(Number.isFinite(POLL_INTERVAL_MS) && POLL_INTERVAL_MS > 0 ? POLL_INTERVAL_MS : 2000);
  }
}

process.on("SIGINT", () => {
  console.log("\n[ue-chat-agent] stopping");
  process.exit(0);
});

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
