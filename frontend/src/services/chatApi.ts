/**
 * 对话 SSE 客户端，与 axios 行程 API 解耦。
 * 使用 fetch + ReadableStream，支持 POST body 与 AbortSignal。
 */

import { API_BASE_URL } from "./api";
import type { ChatSseHandlers, ChatStreamRequest } from "../types/chat";

function parseSseChunk(
  raw: string,
  handlers: ChatSseHandlers,
): void {
  const blocks = raw.split("\n\n");
  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    let eventName = "message";
    const dataLines: string[] = [];

    for (const line of trimmed.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (!dataLines.length) continue;

    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    } catch {
      continue;
    }

    switch (eventName as string) {
      case "status":
        handlers.onStatus?.(String(payload.status ?? ""));
        break;
      case "token":
        handlers.onToken?.(String(payload.text ?? ""));
        break;
      case "error":
        handlers.onError?.(String(payload.message ?? "未知错误"));
        break;
      case "done":
        handlers.onDone?.(Boolean(payload.ok));
        break;
      case "tool_start":
        handlers.onToolStart?.(payload);
        break;
      case "tool_result":
        handlers.onToolResult?.(payload);
        break;
      default:
        break;
    }
  }
}

/**
 * 发起流式对话；返回 Promise 在流结束或 abort 时 resolve/reject。
 */
export async function streamChat(
  request: ChatStreamRequest,
  handlers: ChatSseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `对话接口 HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error("浏览器不支持流式响应 body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        parseSseChunk(part, handlers);
      }
    }

    if (buffer.trim()) {
      parseSseChunk(buffer, handlers);
    }
  } finally {
    reader.releaseLock();
  }
}
