/**
 * 对话助手 Markdown 安全渲染。
 */

import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
  breaks: true,
  gfm: true,
});

export function renderMarkdown(source: string): string {
  const text = (source || "").trimEnd();
  if (!text) return "";

  const html = marked.parse(text, { async: false }) as string;
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  });
}
