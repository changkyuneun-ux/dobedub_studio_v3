import { SystemStatusResponse } from "../api/client";

export async function copyText(text: string) {
  if (!text) {
    return;
  }
  try {
    await navigator.clipboard?.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
}

export function serviceStatusLabel(configured: boolean, error: string, override?: string) {
  if (error) {
    return "FAIL";
  }
  if (override) {
    return override;
  }
  return configured ? "ONLINE" : "CHECK";
}

export function qwenStatusLabel(promptLlm: SystemStatusResponse["promptLlm"] | undefined, error: string) {
  if (error) {
    return "FAIL";
  }
  const provider = (promptLlm?.provider || "mock").toLowerCase();
  if (provider === "mock") {
    return "MOCK";
  }
  return promptLlm?.configured && promptLlm?.apiKeyConfigured ? "ONLINE" : "CHECK";
}


export function compactText(value: string, maxLength: number) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

export function formatTimestamp(value?: string) {
  return String(value || "-").replace(" ", "\n");
}

export function isSuccessStatus(status?: string) {
  return ["completed", "success"].includes(String(status || "").toLowerCase());
}

export function fileUrlWithMode(url: string, mode: "download" | "inline") {
  if (!url || !url.startsWith("/api/files/")) {
    return url;
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}download=${mode === "download" ? "1" : "0"}`;
}

export function formatElapsed(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds || 0));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `00:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

export function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

