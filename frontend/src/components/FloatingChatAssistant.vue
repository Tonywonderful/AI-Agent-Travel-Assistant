<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from "vue";

import { streamChat } from "../services/chatApi";
import type { Itinerary } from "../types";
import type { ChatMessage, ChatUiMessage } from "../types/chat";
import { buildChatContext } from "../utils/chatContext";
import { renderMarkdown } from "../utils/markdown";
import AppIcon from "./AppIcon.vue";

const props = defineProps<{
  itinerary: Itinerary | null;
}>();

const input = ref("");
const messages = ref<ChatUiMessage[]>([]);
const isStreaming = ref(false);
const statusText = ref("");
const errorText = ref("");

let abortController: AbortController | null = null;
let idCounter = 0;

const listRef = ref<HTMLElement | null>(null);

// 助手仅出现在规划页，上下文固定为 planning
const contextHint = computed(() => {
  if (props.itinerary?.destination) {
    return `可参考最近行程：${props.itinerary.destination} · ${props.itinerary.days?.length || 0} 天`;
  }
  return "在规划阶段随时为你解答旅行问题";
});

const quickPrompts = [
  "推荐适合情侣的旅行目的地",
  "帮我规划一个 3 天的轻松行程",
  "预算 5000 能去哪些地方？",
];

function nextId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${Date.now()}-${idCounter}`;
}

async function scrollToBottom() {
  await nextTick();
  const el = listRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

function stopStreaming() {
  abortController?.abort();
  abortController = null;
  isStreaming.value = false;
  statusText.value = "";
}

function clearChat() {
  stopStreaming();
  messages.value = [];
  errorText.value = "";
  input.value = "";
}

async function sendMessage(raw?: string) {
  const text = (raw ?? input.value).trim();
  if (!text || isStreaming.value) return;

  errorText.value = "";
  input.value = "";

  const userMsg: ChatUiMessage = {
    id: nextId("u"),
    role: "user",
    content: text,
  };
  const assistantMsg: ChatUiMessage = {
    id: nextId("a"),
    role: "assistant",
    content: "",
    streaming: true,
  };
  messages.value.push(userMsg, assistantMsg);
  await scrollToBottom();

  const history: ChatMessage[] = messages.value
    .filter((m) => !(m.streaming && !m.content) && !m.error)
    .filter((m) => m.id !== assistantMsg.id)
    .map((m) => ({ role: m.role, content: m.content }));

  if (!history.length || history[history.length - 1].role !== "user") {
    history.push({ role: "user", content: text });
  }

  const context = buildChatContext({
    page: "planning",
    itinerary: props.itinerary,
  });

  isStreaming.value = true;
  statusText.value = "思考中…";
  abortController = new AbortController();

  try {
    await streamChat(
      { messages: history, context },
      {
        onStatus: (status) => {
          if (status === "thinking") statusText.value = "思考中…";
          if (status === "tool") statusText.value = "正在调用工具…";
          if (status === "streaming") statusText.value = "生成中…";
        },
        onToolStart: (payload) => {
          const target = messages.value.find((m) => m.id === assistantMsg.id);
          const name = String(payload.name ?? "tool");
          statusText.value = `正在调用 ${name}…`;
          if (!target) return;
          if (!target.toolTraces) target.toolTraces = [];
          target.toolTraces.push({
            name,
            status: "running",
            args: (payload.args as Record<string, unknown>) || {},
          });
          void scrollToBottom();
        },
        onToolResult: (payload) => {
          const target = messages.value.find((m) => m.id === assistantMsg.id);
          if (!target?.toolTraces?.length) return;
          const name = String(payload.name ?? "");
          const hit =
            [...target.toolTraces].reverse().find((t) => t.name === name && t.status === "running") ||
            target.toolTraces[target.toolTraces.length - 1];
          if (hit) {
            hit.status = payload.ok === false ? "error" : "ok";
            hit.summary = String(payload.summary ?? payload.error ?? "");
          }
          statusText.value = "生成中…";
          void scrollToBottom();
        },
        onToken: (token) => {
          const target = messages.value.find((m) => m.id === assistantMsg.id);
          if (target) {
            target.content += token;
            void scrollToBottom();
          }
        },
        onError: (message) => {
          errorText.value = message;
          const target = messages.value.find((m) => m.id === assistantMsg.id);
          if (target) {
            if (!target.content) {
              target.content = `（出错了）${message}`;
              target.error = true;
            }
          }
        },
        onDone: () => {
          const target = messages.value.find((m) => m.id === assistantMsg.id);
          if (target) {
            target.streaming = false;
            if (!target.content.trim()) {
              target.content = "（没有生成内容，请重试）";
            }
          }
        },
      },
      abortController.signal,
    );
  } catch (err) {
    const aborted =
      (err instanceof DOMException && err.name === "AbortError") ||
      (err instanceof Error && err.name === "AbortError");
    const target = messages.value.find((m) => m.id === assistantMsg.id);
    if (aborted) {
      if (target) {
        target.streaming = false;
        if (!target.content.trim()) {
          target.content = "（已停止生成）";
        }
      }
    } else {
      const message = err instanceof Error ? err.message : "对话请求失败";
      errorText.value = message;
      if (target) {
        target.streaming = false;
        target.error = true;
        if (!target.content.trim()) {
          target.content = `（出错了）${message}`;
        }
      }
    }
  } finally {
    isStreaming.value = false;
    statusText.value = "";
    abortController = null;
    const target = messages.value.find((m) => m.id === assistantMsg.id);
    if (target) target.streaming = false;
    await scrollToBottom();
  }
}

onBeforeUnmount(() => {
  stopStreaming();
});
</script>

<template>
  <section class="chat-side" aria-label="旅行 AI 助手">
    <header class="chat-side__header">
      <div>
        <div class="chat-side__title">旅行 AI 助手</div>
        <div class="chat-side__meta">{{ contextHint }}</div>
      </div>
    </header>

    <section v-if="!messages.length" class="quick-section">
      <h3>快捷提问</h3>
      <button
        v-for="(prompt, index) in quickPrompts"
        :key="prompt"
        type="button"
        class="quick-chip"
        :disabled="isStreaming"
        @click="sendMessage(prompt)"
      >
        <span :class="`quick-chip__icon quick-chip__icon--${index + 1}`">
          <AppIcon :name="index === 0 ? 'users' : index === 1 ? 'wallet' : 'map'" :size="21" />
        </span>
        {{ prompt }}
      </button>
    </section>

    <div ref="listRef" class="chat-side__messages">
      <div v-if="!messages.length" class="chat-empty">
        <span class="bot-avatar"><AppIcon name="bot" :size="19" /></span>
        <div class="chat-empty__bubble">
          你好！我是你的旅行 AI 助手 ✨<br />
          告诉我你的想法，我来帮你规划完美的旅程！
        </div>
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['message-row', msg.role === 'user' ? 'message-row--user' : 'message-row--assistant']"
      >
        <span v-if="msg.role === 'assistant'" class="bot-avatar"><AppIcon name="bot" :size="19" /></span>
        <div :class="['bubble', msg.role === 'user' ? 'bubble--user' : 'bubble--assistant', { 'bubble--error': msg.error }]">
          <div v-if="msg.role === 'assistant' && msg.toolTraces?.length" class="tool-traces">
            <div
              v-for="(trace, idx) in msg.toolTraces"
              :key="`${msg.id}-tool-${idx}`"
              class="tool-trace"
              :class="`tool-trace--${trace.status}`"
            >
              <span class="tool-trace__name">{{ trace.name }}</span>
              <span class="tool-trace__status">{{ trace.status === "running" ? "调用中…" : trace.status === "ok" ? "完成" : "失败" }}</span>
              <div v-if="trace.summary" class="tool-trace__summary">{{ trace.summary }}</div>
            </div>
          </div>
          <div v-if="msg.role === 'assistant'" class="bubble__content markdown-body">
            <div v-html="renderMarkdown(msg.content)" />
            <span v-if="msg.streaming" class="cursor">▍</span>
          </div>
          <div v-else class="bubble__content">{{ msg.content }}</div>
        </div>
      </div>
    </div>

    <div v-if="errorText" class="chat-error">{{ errorText }}</div>
    <div v-if="statusText" class="chat-status">{{ statusText }}</div>

    <footer class="chat-side__footer">
      <button type="button" class="clear-btn" :disabled="isStreaming || !messages.length" @click="clearChat">
        <AppIcon name="trash" :size="15" /> 清空对话
      </button>
      <div class="chat-input-row">
        <input
          v-model="input"
          class="chat-input"
          type="text"
          maxlength="200"
          placeholder="输入你的问题…"
          :disabled="isStreaming"
          @keydown.enter.exact.prevent="sendMessage()"
        />
        <span class="input-count">{{ input.length }}/200</span>
        <button v-if="isStreaming" type="button" class="send-btn send-btn--stop" @click="stopStreaming">停</button>
        <button v-else type="button" class="send-btn" :disabled="!input.trim()" @click="sendMessage()">
          <AppIcon name="send" :size="19" :stroke-width="2.1" />
        </button>
      </div>
    </footer>
  </section>
</template>

<style scoped>
.chat-side {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
}

.chat-side__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.chat-side__header-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.chat-side__avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.chat-side__title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1c1e;
}

.chat-side__meta {
  margin-top: 2px;
  font-size: 12px;
  color: #8e8e93;
  line-height: 1.4;
}

.ghost-btn {
  border: none;
  background: transparent;
  color: #8e8e93;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
}

.ghost-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
  color: #1c1c1e;
}

.ghost-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.chat-side__messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafbfc;
  min-height: 0;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty__bubble {
  align-self: flex-start;
  max-width: 92%;
  padding: 12px 14px;
  border-radius: 14px 14px 14px 4px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  color: #3a3a3c;
  font-size: 13px;
  line-height: 1.55;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.quick-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-chip {
  text-align: left;
  border: 1px solid rgba(37, 99, 235, 0.18);
  background: #fff;
  color: #2563eb;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.quick-chip:hover {
  background: rgba(37, 99, 235, 0.05);
}

.tool-traces {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.tool-trace {
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 11px;
  line-height: 1.4;
  background: rgba(37, 99, 235, 0.06);
  border: 0.5px solid rgba(37, 99, 235, 0.15);
}

.tool-trace--running {
  border-color: rgba(255, 149, 0, 0.35);
  background: rgba(255, 149, 0, 0.08);
}

.tool-trace--error {
  border-color: rgba(255, 59, 48, 0.35);
  background: rgba(255, 59, 48, 0.06);
}

.tool-trace__name {
  font-weight: 600;
  margin-right: 6px;
}

.tool-trace__status {
  opacity: 0.75;
}

.tool-trace__summary {
  margin-top: 3px;
  opacity: 0.9;
  word-break: break-word;
}

.bubble {
  max-width: 90%;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.bubble--user {
  align-self: flex-end;
  background: #2563eb;
  color: #fff;
  border-radius: 14px 14px 4px 14px;
}

.bubble--assistant {
  align-self: flex-start;
  border-radius: 14px 14px 14px 4px;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.bubble--error {
  border: 0.5px solid rgba(255, 59, 48, 0.35);
}

.bubble__content {
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.markdown-body {
  white-space: normal;
}

.markdown-body :deep(> *:first-child) {
  margin-top: 0;
}

.markdown-body :deep(> *:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 0.7em 0 0.35em;
  font-weight: 650;
  line-height: 1.35;
  color: #1c1c1e;
}

.markdown-body :deep(p) {
  margin: 0.35em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.25em;
}

.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.92em;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  padding: 0.1em 0.35em;
}

.markdown-body :deep(pre) {
  margin: 0.45em 0;
  padding: 8px 10px;
  overflow-x: auto;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-body :deep(a) {
  color: #2563eb;
  text-decoration: none;
}

.cursor {
  display: inline-block;
  margin-left: 1px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.chat-error {
  padding: 6px 16px 0;
  color: #ff3b30;
  font-size: 12px;
  flex-shrink: 0;
}

.chat-status {
  padding: 6px 16px 0;
  color: #8e8e93;
  font-size: 12px;
  flex-shrink: 0;
}

.chat-side__footer {
  padding: 12px 14px 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  flex-shrink: 0;
}

.chat-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-input {
  flex: 1;
  min-width: 0;
  height: 40px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 20px;
  padding: 0 14px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  background: #f5f6f8;
}

.chat-input:focus {
  border-color: rgba(37, 99, 235, 0.45);
  background: #fff;
}

.send-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn--stop {
  background: #1c1c1e;
  font-size: 12px;
}
</style>

<style scoped>
.chat-side {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: #172033;
  background: #fff;
}

.chat-side__header {
  height: calc(86px * var(--ui-scale));
  flex: 0 0 calc(86px * var(--ui-scale));
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: calc(19px * var(--ui-scale)) calc(16px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border: 0;
}

.chat-side__title {
  color: #121827;
  font-size: calc(19px * var(--ui-scale));
  line-height: 1.2;
  font-weight: 750;
}

.chat-side__meta {
  margin-top: calc(7px * var(--ui-scale));
  color: #687791;
  font-size: calc(13px * var(--ui-scale));
  line-height: 1.2;
}

.quick-section {
  flex: 0 0 calc(210px * var(--ui-scale));
  padding: calc(6px * var(--ui-scale)) calc(15px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border-bottom: 1px solid #e7edf4;
}

.quick-section h3 {
  margin: 0 0 calc(11px * var(--ui-scale));
  color: #293750;
  font-size: calc(14px * var(--ui-scale));
  font-weight: 650;
}

.quick-chip {
  width: 100%;
  height: calc(43px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(13px * var(--ui-scale));
  margin-bottom: calc(12px * var(--ui-scale));
  padding: 0 calc(15px * var(--ui-scale));
  text-align: left;
  color: #26344d;
  border: 1px solid #cdd9e7;
  border-radius: calc(14px * var(--ui-scale));
  background: #fff;
  font-size: calc(13px * var(--ui-scale));
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.quick-chip:hover:not(:disabled) {
  border-color: #78b8ff;
  background: #f8fbff;
}

.quick-chip:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.quick-chip__icon {
  display: grid;
  place-items: center;
}

.quick-chip__icon--1 { color: #08af70; }
.quick-chip__icon--2 { color: #8358ef; }
.quick-chip__icon--3 { color: #187bf5; }

.chat-side__messages {
  flex: 1;
  min-height: 0;
  padding: calc(14px * var(--ui-scale)) calc(15px * var(--ui-scale));
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: calc(14px * var(--ui-scale));
  background: #fff;
  scrollbar-width: thin;
  scrollbar-color: #d9e2ec transparent;
}

.chat-empty,
.message-row {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: calc(10px * var(--ui-scale));
}

.message-row--user {
  justify-content: flex-end;
}

.bot-avatar {
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: #0878f5;
  border: 1px solid #d9e5f2;
  border-radius: 50%;
  background: #edf5ff;
}

.chat-empty__bubble,
.bubble {
  max-width: calc(100% - (40px * var(--ui-scale)));
  padding: calc(11px * var(--ui-scale)) calc(14px * var(--ui-scale));
  color: #2d3b55;
  border: 1px solid #dfe6ef;
  border-radius: calc(14px * var(--ui-scale));
  background: #fff;
  box-shadow: 0 1px 3px rgba(31, 55, 80, 0.05);
  font-size: calc(13px * var(--ui-scale));
  line-height: 1.6;
}

.chat-empty__bubble {
  border-radius: calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(4px * var(--ui-scale));
}

.bubble--assistant {
  align-self: auto;
  border-radius: calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(4px * var(--ui-scale));
}

.bubble--user {
  max-width: 82%;
  color: #fff;
  border: 0;
  border-radius: calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: linear-gradient(135deg, #228bff, #0876f5);
  box-shadow: 0 3px 8px rgba(0, 105, 235, 0.18);
}

.bubble__content {
  font-size: calc(13px * var(--ui-scale));
  line-height: 1.6;
}

.tool-traces {
  margin-bottom: calc(8px * var(--ui-scale));
}

.chat-error,
.chat-status {
  padding: calc(4px * var(--ui-scale)) calc(16px * var(--ui-scale));
}

.chat-side__footer {
  flex: 0 0 auto;
  padding: 0 calc(14px * var(--ui-scale)) calc(17px * var(--ui-scale));
  border: 0;
  background: #fff;
}

.clear-btn {
  height: calc(32px * var(--ui-scale));
  display: inline-flex;
  align-items: center;
  gap: calc(7px * var(--ui-scale));
  margin-bottom: calc(10px * var(--ui-scale));
  padding: 0 calc(13px * var(--ui-scale));
  color: #5c6e87;
  border: 1px solid #d6e0eb;
  border-radius: calc(16px * var(--ui-scale));
  background: #fff;
  font-size: calc(12px * var(--ui-scale));
  cursor: pointer;
}

.clear-btn .app-icon {
  color: #ff3c47;
}

.clear-btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.chat-input-row {
  position: relative;
  height: calc(60px * var(--ui-scale));
  gap: 0;
  padding: 0 calc(7px * var(--ui-scale)) 0 calc(13px * var(--ui-scale));
  border: 1px solid #d2ddea;
  border-radius: calc(18px * var(--ui-scale));
  background: #fff;
}

.chat-input {
  height: calc(58px * var(--ui-scale));
  padding: 0 calc(76px * var(--ui-scale)) 0 0;
  color: #33445f;
  border: 0;
  border-radius: 0;
  background: transparent;
  font-size: calc(13px * var(--ui-scale));
}

.chat-input:focus {
  border: 0;
  background: transparent;
}

.input-count {
  position: absolute;
  right: calc(61px * var(--ui-scale));
  top: calc(23px * var(--ui-scale));
  color: #95a2b5;
  font-size: calc(10px * var(--ui-scale));
}

.send-btn {
  width: calc(39px * var(--ui-scale));
  height: calc(39px * var(--ui-scale));
  flex: 0 0 calc(39px * var(--ui-scale));
  display: grid;
  place-items: center;
  padding: 0;
  color: #fff;
  border: 0;
  border-radius: 50%;
  background: linear-gradient(145deg, #2a8cff, #126de9);
  box-shadow: 0 4px 9px rgba(13, 105, 224, 0.22);
}

.send-btn:disabled {
  opacity: 0.45;
}

.send-btn--stop {
  font-size: calc(12px * var(--ui-scale));
  background: #29364b;
}
</style>
