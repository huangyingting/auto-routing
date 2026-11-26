import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";
import { formatDebugLog } from "../src/debug-log.mjs";
import { postJsonWithRetry, setLiveDebugLogger } from "../src/live-runners.mjs";

test("formats readable live-call lines without undefined values", () => {
  const line = formatDebugLog("LIVE-CALL", {
    timestamp: "2026-11-26T05:00:00.000Z",
    kind: "call-complete",
    callId: "abc12345",
    backend: "foundry-router",
    status: 200,
    wallMs: 27,
    responseModel: "DeepSeek-V4.1-Flash",
    ignored: undefined,
  });
  assert.equal(
    line,
    "2026-11-26T05:00:00.000Z [LIVE-CALL abc12345] COMPLETE backend=foundry-router status=200 wallMs=27 responseModel=DeepSeek-V4.1-Flash",
  );
});

test("HTTP execution emits start and completion events with a sanitized target", async (t) => {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ model: "test-model", ok: true }));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());

  const { port } = server.address();
  const events = [];
  setLiveDebugLogger((event) => events.push(event));
  t.after(() => setLiveDebugLogger(null));

  await postJsonWithRetry(
    `http://127.0.0.1:${port}/openai/v1/chat/completions?secret=must-not-appear`,
    { "Content-Type": "application/json", "api-key": "must-not-appear" },
    { model: "auto", messages: [{ role: "user", content: "hello" }] },
    "Foundry Model Router",
    { backend: "foundry-router", model: "auto", authSource: "test" },
  );

  assert.equal(events.length, 2);
  assert.equal(events[0].kind, "call-start");
  assert.equal(events[0].target, "/openai/v1/chat/completions");
  assert.equal(events[1].kind, "call-complete");
  assert.equal(events[1].status, 200);
  assert.equal(events[1].responseModel, "test-model");
  assert.equal(JSON.stringify(events).includes("must-not-appear"), false);
});
