/**
 * 把页面状态转换为 ChatContext，集中在一处，方便检查与单测。
 */

import type { Itinerary } from "../types";
import type { ChatContext, ChatItineraryContext, ChatPage } from "../types/chat";

export function buildItineraryContext(
  itinerary: Itinerary | null | undefined,
): ChatItineraryContext | null {
  if (!itinerary) return null;

  const dayTitles = (itinerary.days || []).map((day) => {
    const spotNames = (day.spots || [])
      .map((s) => s.name)
      .filter(Boolean)
      .slice(0, 3)
      .join("、");
    const theme = day.theme?.trim();
    const label = theme || spotNames || "行程安排";
    return `第${day.day_index}天：${label}${spotNames && theme ? `（${spotNames}）` : ""}`;
  });

  return {
    trip_id: itinerary.trip_id,
    destination: itinerary.destination,
    summary: itinerary.summary,
    day_count: itinerary.days?.length ?? 0,
    estimated_budget: itinerary.estimated_budget,
    day_titles: dayTitles,
  };
}

export function buildChatContext(options: {
  page: ChatPage;
  itinerary?: Itinerary | null;
}): ChatContext {
  return {
    page: options.page,
    itinerary: buildItineraryContext(options.itinerary),
    planning: null,
    extra: {},
  };
}

export function viewToChatPage(view: "home" | "result" | "history"): ChatPage {
  if (view === "home") return "planning";
  if (view === "result") return "result";
  return "history";
}
