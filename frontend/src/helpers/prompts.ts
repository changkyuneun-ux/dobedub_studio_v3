import { HistoryItem, HistorySegment, PromptEntry, PromptTerm } from "../api/client";

export function positivePromptEntries(item: HistoryItem): PromptEntry[] {
  return normalizePromptEntries(item.positivePrompts, item.segments, "positive", item.positivePrompt || item.prompt || "");
}

export function negativePromptEntries(item: HistoryItem): PromptEntry[] {
  return normalizePromptEntries(item.negativePrompts, item.segments, "negative", item.negativePrompt || "");
}

export function normalizePromptEntries(
  entries: PromptEntry[] | undefined,
  segments: HistorySegment[] | undefined,
  type: "positive" | "negative",
  fallback: string
): PromptEntry[] {
  if (entries?.length) {
    return entries
      .map((entry, index) => ({ index: Number(entry.index || index + 1), text: promptText(entry) }))
      .filter((entry) => entry.text);
  }
  const fromSegments = (segments || [])
    .map((segment, index) => ({
      index: Number(segment.index || index + 1),
      text: String(
        type === "positive"
          ? segment.positivePrompt || ""
          : segment.negativePromptAddition || segment.negativePrompt || ""
      ).trim()
    }))
    .filter((entry) => entry.text);
  if (fromSegments.length) {
    return fromSegments;
  }
  return splitPromptList(fallback);
}

export function splitPromptList(value: string): PromptEntry[] {
  const text = String(value || "").trim();
  if (!text) {
    return [];
  }
  const parts = text.split("|").map((part) => part.trim()).filter(Boolean);
  return (parts.length ? parts : [text]).map((part, index) => ({
    index: index + 1,
    text: part.replace(/^\s*\d+\s*[:.)-]\s*/, "").trim()
  }));
}

export function promptText(prompt: PromptEntry | string | undefined) {
  return String(typeof prompt === "string" ? prompt : prompt?.text || prompt?.prompt || "").trim();
}

export function promptForSegment(prompts: PromptEntry[], segmentIndex: number) {
  return promptText(prompts.find((prompt) => Number(prompt.index) === segmentIndex) || prompts[segmentIndex - 1]);
}

export function promptKeywordText(keywords: PromptTerm[]) {
  return keywords.map((keyword) => keyword.labelEn || keyword.code).filter(Boolean).join(", ");
}

export function combinePromptText(...parts: Array<string | undefined | null>) {
  const seen = new Set<string>();
  const tokens = parts
    .flatMap((part) => String(part || "").split(","))
    .map((part) => part.trim())
    .filter(Boolean)
    .filter((part) => {
      const key = part.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  return tokens.join(", ");
}

// C-01: generate_prompt가 반환하는 {code, message, severity} 경고를 화면 2b
// 설계대로 심각도별로 묶는다. 백엔드는 severity로 "info"/"warning"/"error"만
// 사용하므로(prompt_builder_service.py), 알 수 없는 값은 "warning"으로 취급한다.
export type PromptWarningSeverity = "error" | "warning" | "info";

export function normalizePromptWarningSeverity(severity?: string): PromptWarningSeverity {
  if (severity === "error") return "error";
  if (severity === "info") return "info";
  return "warning";
}

export function groupPromptWarningsBySeverity(
  warnings: Array<{ code?: string; message?: string; severity?: string }>,
) {
  const order: PromptWarningSeverity[] = ["error", "warning", "info"];
  return order
    .map((severity) => ({
      severity,
      items: warnings.filter((warning) => normalizePromptWarningSeverity(warning.severity) === severity),
    }))
    .filter((group) => group.items.length > 0);
}

export function formatPromptList(prompts: PromptEntry[] | undefined) {
  return (prompts || [])
    .filter((prompt) => promptText(prompt))
    .map((prompt, index) => `${prompt.index || index + 1}. ${promptText(prompt)}`)
    .join("\n");
}

