function formatValue(value) {
  if (Array.isArray(value)) return value.join(",");
  if (typeof value === "string" && /\s/.test(value)) return JSON.stringify(value);
  return String(value);
}

export function formatDebugLog(scope, event) {
  const timestamp = event.timestamp || new Date().toISOString();
  const action = String(event.kind || "event").replace(/^(call|step)-/, "").toUpperCase();
  const call = event.callId ? ` ${event.callId}` : "";
  const fields = Object.entries(event)
    .filter(([key, value]) => !["timestamp", "kind", "callId"].includes(key) && value !== null && value !== undefined)
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join(" ");
  return `${timestamp} [${scope}${call}] ${action}${fields ? ` ${fields}` : ""}`;
}
