/** 对话类型；与行程 types 解耦，便于单独检查与扩展。 */

export type ChatRole = "user" | "assistant" | "system";
export type ChatPage = "planning" | "result" | "history";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatItineraryContext {
  trip_id?: string | null;
  destination?: string | null;
  summary?: string | null;
  day_count?: number | null;
  estimated_budget?: number | null;
  day_titles?: string[];
}

export interface ChatPlanningContext {
  destination?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  travelers?: number | null;
  budget?: number | null;
  pace?: string | null;
  preferences?: string[];
  dietary_preferences?: string[];
  hotel_level?: string | null;
  special_notes?: string | null;
}

export interface ChatContext {
  page: ChatPage;
  itinerary?: ChatItineraryContext | null;
  planning?: ChatPlanningContext | null;
  extra?: Record<string, unknown>;
}

export interface ChatStreamRequest {
  messages: ChatMessage[];
  context: ChatContext;
}

/** 前端本地消息（含流式占位状态） */
export interface ChatUiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  error?: boolean;
  toolTraces?: ChatToolTrace[];
}

export interface ChatToolTrace {
  name: string;
  status: "running" | "ok" | "error";
  summary?: string;
  args?: Record<string, unknown>;
}

export type ChatSseEventName = "status" | "token" | "error" | "done" | "tool_start" | "tool_result";

export interface ChatSseHandlers {
  onStatus?: (status: string) => void;
  onToken?: (text: string) => void;
  onError?: (message: string) => void;
  onDone?: (ok: boolean) => void;
  onToolStart?: (payload: Record<string, unknown>) => void;
  onToolResult?: (payload: Record<string, unknown>) => void;
}
