<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import { streamChat } from "../services/chatApi";
import type { Itinerary } from "../types";
import type { ChatMessage, ChatUiMessage } from "../types/chat";
import { buildChatContext, viewToChatPage } from "../utils/chatContext";
import { renderMarkdown } from "../utils/markdown";

const props = defineProps<{
  currentView: "home" | "result" | "history";
  itinerary: Itinerary | null;
}>();

const open = ref(false);
const input = ref("");
const messages = ref<ChatUiMessage[]>([]);
const isStreaming = ref(false);
const statusText = ref("");
const errorText = ref("");

let abortController: AbortController | null = null;
let idCounter = 0;

const listRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);

/** 面板左上角坐标；null 表示使用默认右下角定位 */
const panelPos = ref<{ x: number; y: number } | null>(null);
const isDragging = ref(false);
let dragOffsetX = 0;
let dragOffsetY = 0;

const pageLabel = computed(() => {
  if (props.currentView === "home") return "规划页";
  if (props.currentView === "result") return "结果页";
  return "历史页";
});

const contextHint = computed(() => {
  if (props.itinerary?.destination) {
    return `已携带行程：${props.itinerary.destination} · ${props.itinerary.days?.length || 0} 天`;
  }
  return "当前无行程上下文，可先聊规划思路";
});

const quickPrompts = computed(() => {
  if (props.itinerary) {
    return [
      "这几天天气怎么样？适合看日落吗？",
      "第一天主要景点之间开车大概多久？",
      "帮我概括这份行程的亮点",
    ];
  }
  return [
    "大理最近天气怎么样？",
    "搜索大理古城附近的餐厅",
    "大理古城到双廊大概多远？",
  ];
});

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

  // 确保最后一条是刚发的 user
  if (!history.length || history[history.length - 1].role !== "user") {
    history.push({ role: "user", content: text });
  }

  const context = buildChatContext({
    page: viewToChatPage(props.currentView),
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

function onFabClick() {
  open.value = !open.value;
}

function clampPanelPosition(x: number, y: number): { x: number; y: number } {
  const panel = panelRef.value;
  const width = panel?.offsetWidth ?? 380;
  const height = panel?.offsetHeight ?? 560;
  const margin = 8;
  const maxX = Math.max(margin, window.innerWidth - width - margin);
  const maxY = Math.max(margin, window.innerHeight - height - margin);
  return {
    x: Math.min(Math.max(margin, x), maxX),
    y: Math.min(Math.max(margin, y), maxY),
  };
}

function onDragPointerMove(e: PointerEvent) {
  if (!isDragging.value) return;
  panelPos.value = clampPanelPosition(e.clientX - dragOffsetX, e.clientY - dragOffsetY);
}

function onDragPointerUp() {
  if (!isDragging.value) return;
  isDragging.value = false;
  window.removeEventListener("pointermove", onDragPointerMove);
  window.removeEventListener("pointerup", onDragPointerUp);
}

function onHeaderPointerDown(e: PointerEvent) {
  const target = e.target as HTMLElement | null;
  if (target?.closest("button")) return;

  const panel = panelRef.value;
  if (!panel) return;

  const rect = panel.getBoundingClientRect();
  // 首次拖动：从当前渲染位置接管坐标
  if (!panelPos.value) {
    panelPos.value = { x: rect.left, y: rect.top };
  }

  isDragging.value = true;
  dragOffsetX = e.clientX - rect.left;
  dragOffsetY = e.clientY - rect.top;
  window.addEventListener("pointermove", onDragPointerMove);
  window.addEventListener("pointerup", onDragPointerUp);
  e.preventDefault();
}

function onWindowResize() {
  if (!panelPos.value) return;
  panelPos.value = clampPanelPosition(panelPos.value.x, panelPos.value.y);
}

const panelStyle = computed(() => {
  if (!panelPos.value) return undefined;
  return {
    left: `${panelPos.value.x}px`,
    top: `${panelPos.value.y}px`,
    right: "auto",
    bottom: "auto",
  };
});

watch(open, (value) => {
  if (value) void scrollToBottom();
});

window.addEventListener("resize", onWindowResize);
onBeforeUnmount(() => {
  window.removeEventListener("resize", onWindowResize);
  window.removeEventListener("pointermove", onDragPointerMove);
  window.removeEventListener("pointerup", onDragPointerUp);
});
</script>

<template>
  <div class="chat-root">
    <Transition name="chat-panel">
      <section
        v-if="open"
        ref="panelRef"
        class="chat-panel"
        :class="{ 'chat-panel--dragging': isDragging, 'chat-panel--custom-pos': !!panelPos }"
        :style="panelStyle"
        aria-label="旅行 AI 助手"
      >
        <header
          class="chat-panel__header"
          @pointerdown="onHeaderPointerDown"
        >
          <div>
            <div class="chat-panel__title">旅行 AI 助手</div>
            <div class="chat-panel__meta">
              {{ pageLabel }} · {{ contextHint }}
            </div>
          </div>
          <div class="chat-panel__header-actions">
            <button type="button" class="ghost-btn" :disabled="isStreaming" @click="clearChat">
              清空
            </button>
            <button type="button" class="ghost-btn" @click="open = false">关闭</button>
          </div>
        </header>

        <div ref="listRef" class="chat-panel__messages">
          <div v-if="!messages.length" class="chat-empty">
            <p>流式对话 + 工具（天气 / 地图 / 路线 / 联网搜索）。</p>
            <p>模型会在需要实时信息时自动调用工具；也可先聊规划思路。</p>
            <div class="quick-list">
              <button
                v-for="prompt in quickPrompts"
                :key="prompt"
                type="button"
                class="quick-chip"
                @click="sendMessage(prompt)"
              >
                {{ prompt }}
              </button>
            </div>
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['bubble', msg.role === 'user' ? 'bubble--user' : 'bubble--assistant', { 'bubble--error': msg.error }]"
          >
            <div class="bubble__role">{{ msg.role === "user" ? "我" : "助手" }}</div>
            <div
              v-if="msg.role === 'assistant' && msg.toolTraces?.length"
              class="tool-traces"
            >
              <div
                v-for="(trace, idx) in msg.toolTraces"
                :key="`${msg.id}-tool-${idx}`"
                class="tool-trace"
                :class="`tool-trace--${trace.status}`"
              >
                <span class="tool-trace__name">{{ trace.name }}</span>
                <span class="tool-trace__status">
                  {{
                    trace.status === "running"
                      ? "调用中…"
                      : trace.status === "ok"
                        ? "完成"
                        : "失败"
                  }}
                </span>
                <div v-if="trace.summary" class="tool-trace__summary">{{ trace.summary }}</div>
              </div>
            </div>
            <div
              v-if="msg.role === 'assistant'"
              class="bubble__content markdown-body"
            >
              <div v-html="renderMarkdown(msg.content)" />
              <span v-if="msg.streaming" class="cursor">▍</span>
            </div>
            <div v-else class="bubble__content">
              {{ msg.content }}
            </div>
          </div>
        </div>

        <div v-if="errorText" class="chat-error">{{ errorText }}</div>
        <div v-if="statusText" class="chat-status">{{ statusText }}</div>

        <footer class="chat-panel__footer">
          <textarea
            v-model="input"
            class="chat-input"
            rows="2"
            placeholder="问问行程、预算、节奏…（Enter 发送，Shift+Enter 换行）"
            :disabled="isStreaming"
            @keydown.enter.exact.prevent="sendMessage()"
          />
          <div class="chat-panel__footer-actions">
            <button
              v-if="isStreaming"
              type="button"
              class="btn btn--ghost"
              @click="stopStreaming"
            >
              停止
            </button>
            <button
              type="button"
              class="btn btn--primary"
              :disabled="isStreaming || !input.trim()"
              @click="sendMessage()"
            >
              发送
            </button>
          </div>
        </footer>
      </section>
    </Transition>

    <button
      type="button"
      class="chat-fab"
      :class="{ 'chat-fab--open': open }"
      :aria-expanded="open"
      aria-label="打开旅行 AI 助手"
      @click="onFabClick"
    >
      <span v-if="!open">AI</span>
      <span v-else>×</span>
    </button>
  </div>
</template>

<style scoped>
.chat-root {
  position: fixed;
  inset: 0;
  z-index: 200;
  pointer-events: none;
}

.chat-fab,
.chat-panel {
  pointer-events: auto;
}

.chat-fab {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #2f6bff, #5b8cff);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(47, 107, 255, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.chat-fab:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(47, 107, 255, 0.4);
}

.chat-fab:active {
  transform: scale(0.96);
}

.chat-fab--open {
  background: #1c1c1e;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.chat-panel {
  position: fixed;
  right: 20px;
  bottom: 88px;
  width: min(380px, calc(100vw - 32px));
  height: min(560px, calc(100vh - 120px));
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.96);
  border: 0.5px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.14);
  overflow: hidden;
  backdrop-filter: blur(12px);
}

.chat-panel--custom-pos {
  right: auto;
  bottom: auto;
}

.chat-panel--dragging {
  user-select: none;
  box-shadow: 0 20px 56px rgba(0, 0, 0, 0.2);
}

.chat-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 14px 10px;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.06);
  cursor: grab;
  touch-action: none;
}

.chat-panel--dragging .chat-panel__header {
  cursor: grabbing;
}

.chat-panel__title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1c1e;
}

.chat-panel__meta {
  margin-top: 2px;
  font-size: 12px;
  color: #8e8e93;
  line-height: 1.4;
  max-width: 240px;
}

.chat-panel__header-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.ghost-btn {
  border: none;
  background: transparent;
  color: #8e8e93;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
}

.ghost-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
  color: #1c1c1e;
}

.ghost-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f7f7fa;
}

.chat-empty {
  font-size: 13px;
  color: #636366;
  line-height: 1.55;
}

.chat-empty p {
  margin: 0 0 8px;
}

.quick-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.quick-chip {
  text-align: left;
  border: 0.5px solid rgba(47, 107, 255, 0.25);
  background: #fff;
  color: #2f6bff;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  cursor: pointer;
}

.quick-chip:hover {
  background: rgba(47, 107, 255, 0.06);
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
  background: rgba(47, 107, 255, 0.06);
  border: 0.5px solid rgba(47, 107, 255, 0.15);
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
  max-width: 92%;
  padding: 8px 10px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.bubble--user {
  align-self: flex-end;
  background: #2f6bff;
  color: #fff;
}

.bubble--assistant {
  align-self: flex-start;
}

.bubble--error {
  border: 0.5px solid rgba(255, 59, 48, 0.35);
}

.bubble__role {
  font-size: 11px;
  opacity: 0.7;
  margin-bottom: 2px;
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
  background: rgba(47, 107, 255, 0.06);
  border: 0.5px solid rgba(47, 107, 255, 0.15);
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

.markdown-body :deep(h1) {
  font-size: 1.15em;
}

.markdown-body :deep(h2) {
  font-size: 1.08em;
}

.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  font-size: 1em;
}

.markdown-body :deep(p) {
  margin: 0.35em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.25em;
}

.markdown-body :deep(li) {
  margin: 0.2em 0;
}

.markdown-body :deep(li > p) {
  margin: 0.15em 0;
}

.markdown-body :deep(strong) {
  font-weight: 650;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 0.5px solid rgba(0, 0, 0, 0.12);
  margin: 0.75em 0;
}

.markdown-body :deep(blockquote) {
  margin: 0.45em 0;
  padding: 0.15em 0 0.15em 0.75em;
  border-left: 3px solid rgba(47, 107, 255, 0.35);
  color: #636366;
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
  color: #2f6bff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
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
  padding: 6px 14px 0;
  color: #ff3b30;
  font-size: 12px;
}

.chat-status {
  padding: 6px 14px 0;
  color: #8e8e93;
  font-size: 12px;
}

.chat-panel__footer {
  padding: 10px 12px 12px;
  border-top: 0.5px solid rgba(0, 0, 0, 0.06);
  background: #fff;
}

.chat-input {
  width: 100%;
  resize: none;
  border: 0.5px solid rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  background: #fafafa;
}

.chat-input:focus {
  border-color: rgba(47, 107, 255, 0.45);
  background: #fff;
}

.chat-panel__footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn {
  border: none;
  border-radius: 10px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn--primary {
  background: #2f6bff;
  color: #fff;
}

.btn--ghost {
  background: rgba(0, 0, 0, 0.05);
  color: #1c1c1e;
}

.chat-panel-enter-active,
.chat-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.chat-panel-enter-from,
.chat-panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (max-width: 768px) {
  .chat-fab {
    right: 16px;
    bottom: 16px;
  }

  .chat-panel {
    right: 16px;
    bottom: 80px;
    width: min(100vw - 24px, 380px);
    height: min(70vh, 560px);
  }
}
</style>
