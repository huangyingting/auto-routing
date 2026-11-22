#!/usr/bin/env node
/**
 * Local Interactive Demo Studio server (http://127.0.0.1:8787).
 * Drives real live execution via GitHub Copilot CLI (`fusion`), Microsoft Foundry Model Router (`foundry`),
 * local HTTP 429->200 failover (`foundry` Step 5), and Microsoft-Decision-1.1 `/v1/systemone` (`decision`),
 * with optional fallback to verified recordings when cloud env vars are not set.
 */
import { readFile, rm } from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  detectLiveCapabilities,
  probeCustomPromptLive,
  runDecisionStepLive,
  runFoundryStepLive,
  runFusionStepLive,
} from "./live-runners.mjs";

const demoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(demoRoot, "..");
const htmlPath = path.join(repoRoot, "dist", "html", "index.html");
const recordingsPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");
const port = Number.parseInt(process.env.AUTO_DEMO_PORT ?? "8787", 10);

const clients = new Set();
let busy = false;
const sessionStore = {};

function send(event) {
  const payload = `data: ${JSON.stringify(event)}\n\n`;
  for (const client of clients) client.write(payload);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function cleanupSessionStore() {
  if (sessionStore.fusionDir) {
    const dir = sessionStore.fusionDir;
    delete sessionStore.fusionDir;
    delete sessionStore.fusionSessionId;
    delete sessionStore.prevFusionStats;
    await rm(dir, { recursive: true, force: true }).catch(() => {});
  }
}

async function playRecorded(demo, step, note = null) {
  const recordings = JSON.parse(await readFile(recordingsPath, "utf8"));
  const seq = recordings.steps?.[demo]?.[String(step)];
  if (!seq) throw new Error(`Unknown demo=${demo} step=${step}`);
  for (const item of seq) {
    if (item.delayMs > 0) await sleep(Math.min(180, item.delayMs));
    if (item.event.kind === "step-start") {
      send(item.event);
      if (note) send({ kind: "output", text: `[Note] ${note}\n` });
    } else {
      send(item.event);
    }
  }
}

async function runStep(demo, step, mode = "auto") {
  busy = true;
  try {
    if (mode === "replay") {
      await playRecorded(demo, step);
      return;
    }

    const caps = detectLiveCapabilities();

    if (demo === "fusion") {
      if (caps.copilotAvailable) {
        await runFusionStepLive(step, send, sessionStore);
        return;
      }
      if (mode === "live") {
        throw new Error("GitHub Copilot CLI (`copilot`) is not available on PATH.");
      }
      await playRecorded(demo, step, "Copilot CLI not found on PATH -> showing verified replay.");
      return;
    }

    if (demo === "foundry") {
      if (step === 5 || caps.foundryReady) {
        await runFoundryStepLive(step, send);
        return;
      }
      if (mode === "live") {
        throw new Error("Set AZURE_FOUNDRY_ENDPOINT (+ key or `az login`) to execute live Foundry cloud steps 1–4.");
      }
      await playRecorded(
        demo,
        step,
        "AZURE_FOUNDRY_ENDPOINT not configured -> showing verified replay (Step 5 runs live local HTTP failover).",
      );
      return;
    }

    if (demo === "decision") {
      if (caps.decisionReady) {
        await runDecisionStepLive(step, send);
        return;
      }
      if (mode === "live") {
        throw new Error("Set AZURE_FOUNDRY_ENDPOINT (+ optional DECISION_DEPLOYMENT) to execute live /v1/systemone calls.");
      }
      await playRecorded(
        demo,
        step,
        "AZURE_FOUNDRY_ENDPOINT not configured -> showing verified replay.",
      );
      return;
    }

    throw new Error(`Unknown demo: ${demo}`);
  } finally {
    busy = false;
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${port}`);

  if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/index.html")) {
    const html = await readFile(htmlPath, "utf8");
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(html);
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/meta") {
    const caps = detectLiveCapabilities();
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        baselineModel: "Always Opus / Sol",
        baselineCost: "$0.150 · 4.2s",
        liveCopilot: caps.copilotAvailable,
        liveFoundry: caps.foundryReady,
        liveDecision: caps.decisionReady,
        authSource: caps.authSource,
      }),
    );
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/events") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    });
    res.write(": connected\n\n");
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/run-step") {
    if (busy) {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Another step is currently running." }));
      return;
    }
    const demo = url.searchParams.get("demo") || "fusion";
    const step = Number.parseInt(url.searchParams.get("step") || "1", 10);
    const mode = url.searchParams.get("mode") || "auto";
    res.writeHead(202, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    runStep(demo, step, mode).catch((err) => {
      send({ kind: "step-error", error: err.message || String(err) });
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/custom-prompt") {
    if (busy) {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Busy running another step." }));
      return;
    }
    let body = "";
    for await (const chunk of req) body += chunk;
    const prompt = body.trim();
    res.writeHead(202, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    if (!prompt) return;

    busy = true;
    try {
      const live = await probeCustomPromptLive(prompt);
      if (live) {
        send({ kind: "output", text: `[SOURCE] ${live.source} (--output-format json / HTTP JSON)\n` });
        if (live.rawTrace) {
          send({ kind: "raw", text: `\n──▶ [Live Custom Prompt Probe · Raw Log]\n${live.rawTrace}\n` });
        }
        send({
          kind: "probe-result",
          source: live.source,
          prompt,
          model: live.model,
          meta: live.meta,
          summary: live.summary,
          chips: live.chips,
        });
      } else {
        send({ kind: "probe-fallback", prompt });
      }
    } catch (err) {
      send({ kind: "step-error", error: err.message || String(err) });
    } finally {
      busy = false;
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/cancel") {
    busy = false;
    await cleanupSessionStore();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not Found");
});

process.on("SIGINT", async () => {
  await cleanupSessionStore();
  process.exit(0);
});

server.listen(port, "127.0.0.1", () => {
  const caps = detectLiveCapabilities();
  console.log(`Auto-Routing Interactive Demo Studio listening at http://127.0.0.1:${port}/#22`);
  console.log(
    `Live backends -> Copilot CLI: ${caps.copilotAvailable ? "READY" : "missing"} | Foundry Router: ${caps.foundryReady ? "READY" : "replay-until-AZURE_FOUNDRY_ENDPOINT"} | Decision-1.1: ${caps.decisionReady ? "READY" : "replay-until-AZURE_FOUNDRY_ENDPOINT"}`,
  );
});
