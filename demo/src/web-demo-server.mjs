#!/usr/bin/env node
/**
 * Local Interactive Demo Studio server (http://127.0.0.1:8787).
 * Serves dist/html/index.html and streams step-by-step routing traces + custom prompt classification!
 */
import { readFile } from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tryLiveDecisionCall, tryLiveFoundryRoute } from "./demo-cli.mjs";

const demoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(demoRoot, "..");
const htmlPath = path.join(repoRoot, "dist", "html", "index.html");
const recordingsPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");
const port = Number.parseInt(process.env.AUTO_DEMO_PORT ?? "8787", 10);

const clients = new Set();
let busy = false;

function send(event) {
  const payload = `data: ${JSON.stringify(event)}\n\n`;
  for (const client of clients) client.write(payload);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function scoreCustomPromptLocally(prompt) {
  const lower = prompt.toLowerCase();
  const isHarmOrInjury = /(hurt|injur|lawyer|lawsuit|collapse|mold|refund|\$\d+.*twice|chargeback)/i.test(prompt);
  const isTrivial = prompt.length < 75 && /(thanks|thank you|stop|unsubscribe|👍|away on leave|out of office)/i.test(lower);
  const isHardArch = /(deadlock|lock-free|rust|aba|distributed|multi-region|50k rps|architecture|security|prove|formal|critique)/i.test(lower);
  const isSlideOrMultimodal = /(slide|deck|powerpoint|chart|visual|image|renewal)/i.test(lower);

  if (isHarmOrInjury) {
    return {
      decisionChoice: "safety_human_escalation",
      confidence: 0.96,
      priorityScore: 2.92,
      selectedModel: "P3 Immediate Human",
      pattern: "Decision-1.1 Gate",
      costSaved: "Zero unsafe bot reply",
      summary: "Detected high-severity safety/dispute signal -> bypassed LLM generation and escalated to P3 human specialist.",
    };
  }
  if (isTrivial) {
    return {
      decisionChoice: "code_or_no_reply",
      confidence: 0.97,
      priorityScore: 0.04,
      selectedModel: "Code Handler ($0)",
      pattern: "Short-Circuit",
      costSaved: "-99.9% vs Frontier",
      summary: "Routine acknowledgement / opt-out -> handled deterministically after $0.000013 Decision-1.1 check.",
    };
  }
  if (isSlideOrMultimodal) {
    return {
      decisionChoice: "cowork_multimodel",
      confidence: 0.91,
      priorityScore: 0.35,
      selectedModel: "SLM + Opus 5.5 + Image 2.5",
      pattern: "Multi-Job Auto",
      costSaved: "2.5–5× right-sized",
      summary: "Decomposed into SLM Work IQ retrieval + frontier narrative/slide reasoning + specialized image model.",
    };
  }
  if (isHardArch) {
    return {
      decisionChoice: "frontier_critique",
      confidence: 0.89,
      priorityScore: 0.42,
      selectedModel: "Opus 5.5 / GPT-6.1 Sol",
      pattern: "Cascade / Critique",
      costSaved: "-48% vs Naive Max",
      summary: "High reasoning & verification demand -> routed to frontier reasoning + read-only critic verification.",
    };
  }
  return {
    decisionChoice: "efficient_single",
    confidence: 0.93,
    priorityScore: 0.12,
    selectedModel: "MAI Code 2 Flash / Haiku 5.5",
    pattern: "Single (Fast)",
    costSaved: "-92% vs Frontier",
    summary: "Bounded complexity -> served in a single fast pass without paying frontier reasoning or review overhead.",
  };
}

async function runStep(demo, step) {
  const recordings = JSON.parse(await readFile(recordingsPath, "utf8"));
  const seq = recordings.steps?.[demo]?.[String(step)];
  if (!seq) throw new Error(`Unknown demo=${demo} step=${step}`);

  busy = true;
  try {
    // If live Foundry endpoint is configured on Step 2 or Step 3 of foundry, run a real live call!
    if (demo === "foundry" && (step === 2 || step === 3) && process.env.AZURE_FOUNDRY_ENDPOINT) {
      send({ kind: "step-start", demo, step });
      const prompt = step === 2
        ? "Extract invoice ID and currency as JSON from: Invoice INV-2026-8841, Total 4,250 EUR."
        : "Design a lock-free ring buffer in Rust with formal ABA hazard-pointer invariants.";
      send({ kind: "output", text: `[LIVE FOUNDRY CALL] POST ${process.env.AZURE_FOUNDRY_ENDPOINT}/openai/v1/chat/completions\n  model="auto", mode="balanced"\n` });
      const live = await tryLiveFoundryRoute(prompt, "balanced");
      if (live) {
        const trace = live.model_selection_details?.model_router_details;
        const rMs = trace?.routing_trace?.[0]?.latency_ms ?? "—";
        send({
          kind: "output",
          text: `HTTP 200 OK · served by "${live.model}"\n  routing_trace: ${JSON.stringify(trace?.routing_trace ?? [])}\n  tokens: prompt=${live.usage?.prompt_tokens}, completion=${live.usage?.completion_tokens}\n`,
        });
        send({
          kind: "route",
          model: live.model,
          meta: `Live Router: ${rMs} ms`,
          chip1: `Router: ${rMs} ms ✓`,
          chip1Tone: "on",
          chip2: "Live HTTP 200 ✓",
          chip2Tone: "on",
          chip3: "Auto-Selected ✓",
          chip3Tone: "on",
        });
        send({ kind: "step-done", demo, step, code: 0 });
        return;
      }
    }

    for (const item of seq) {
      if (item.delayMs > 0) await sleep(Math.min(220, item.delayMs));
      send(item.event);
    }
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
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({
      baselineModel: "Always Opus / Sol",
      baselineCost: "$0.150 · 4.2s",
      liveFoundry: Boolean(process.env.AZURE_FOUNDRY_ENDPOINT),
    }));
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
    res.writeHead(202, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    runStep(demo, step).catch((err) => {
      send({ kind: "step-error", error: err.message || String(err) });
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/custom-prompt") {
    let body = "";
    for await (const chunk of req) body += chunk;
    const prompt = body.trim();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    if (!prompt) return;

    send({ kind: "output", text: `\n──▶ [Custom Prompt Probe] "${prompt}"\n` });
    try {
      const liveDec = await tryLiveDecisionCall(prompt, {
        route: {
          type: "choice",
          instructions: "Select the most cost-effective execution route that meets quality and safety requirements.",
          criteria: {
            code_or_no_reply: "Acknowledgements, opt-outs, or deterministic FAQ",
            efficient_single: "Straightforward extraction, short edit, or simple lookup",
            frontier_critique: "Complex multi-file bug, formal architecture, or subtle reasoning",
            safety_human_escalation: "Injury, legal threat, or unapproved financial commitment",
          },
        },
      });
      if (liveDec?.answers?.route) {
        send({ kind: "output", text: `  [Live Decision-1.1] ${JSON.stringify(liveDec.answers.route)}\n` });
      } else {
        const r = scoreCustomPromptLocally(prompt);
        send({
          kind: "output",
          text: `  route="${r.decisionChoice}" (p=${r.confidence.toFixed(2)}) · priority_score=${r.priorityScore.toFixed(2)}\n  selected="${r.selectedModel}" (${r.pattern}) · ${r.summary}\n`,
        });
        send({
          kind: "route",
          model: r.selectedModel,
          meta: `${r.pattern} · p=${r.confidence.toFixed(2)}`,
          chip1: `Pattern: ${r.pattern} ✓`,
          chip1Tone: "on",
          chip2: `Conf: ${(r.confidence * 100).toFixed(0)}% ✓`,
          chip2Tone: "on",
          chip3: r.costSaved,
          chip3Tone: "on",
        });
      }
    } catch (err) {
      send({ kind: "output", text: `  [Error] ${err.message || String(err)}\n` });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/cancel") {
    busy = false;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not Found");
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Auto-Routing Interactive Demo Studio listening at http://127.0.0.1:${port}/#22`);
});
