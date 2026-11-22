#!/usr/bin/env node
/**
 * CLI runner for the three Auto-Routing LLMs demos:
 *   1. fusion   - GitHub Copilot Auto (HyDRA) & Copilot Fusion (Single / Cascade / Critique)
 *   2. foundry  - Microsoft Copilot Auto & Foundry Model Router (Balanced / Cost / Quality + 429 Failover)
 *   3. decision - Microsoft-Decision-1.1 (/providers/microsoft/v1/systemone: choice, score, noul)
 *
 * Pass --live with AZURE_FOUNDRY_ENDPOINT (+ AZURE_FOUNDRY_API_KEY or `az login` bearer token)
 * to execute real live HTTP calls against Foundry Model Router and Microsoft-Decision-1.1.
 */
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");
const recordingsPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");

function parseArgs(argv) {
  let demo = "all";
  let live = false;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--demo" && argv[i + 1]) {
      demo = argv[i + 1];
      i += 1;
    } else if (argv[i] === "--live") {
      live = true;
    }
  }
  return { demo, live };
}

function getBearerToken() {
  if (process.env.AZURE_FOUNDRY_API_KEY) {
    return { headerName: "api-key", headerValue: process.env.AZURE_FOUNDRY_API_KEY };
  }
  if (process.env.AZURE_ENTRA_TOKEN) {
    return { headerName: "Authorization", headerValue: `Bearer ${process.env.AZURE_ENTRA_TOKEN}` };
  }
  try {
    const cmd = process.platform === "win32" ? "az.cmd" : "az";
    const subArgs = process.env.AZURE_SUBSCRIPTION_ID ? ["--subscription", process.env.AZURE_SUBSCRIPTION_ID] : [];
    const token = execFileSync(
      cmd,
      ["account", "get-access-token", ...subArgs, "--resource", "https://cognitiveservices.azure.com", "--query", "accessToken", "-o", "tsv"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
    ).trim();
    if (token) return { headerName: "Authorization", headerValue: `Bearer ${token}` };
  } catch {
    // Fall back to recorded replay when Azure CLI is not signed in.
  }
  return null;
}

export async function tryLiveFoundryRoute(prompt, mode = "balanced") {
  const endpoint = process.env.AZURE_FOUNDRY_ENDPOINT?.replace(/\/+$/, "");
  if (!endpoint) return null;
  const auth = getBearerToken();
  if (!auth) return null;

  const res = await fetch(`${endpoint}/openai/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Foundry-Features": "ModelRouterControls=V1Preview",
      [auth.headerName]: auth.headerValue,
    },
    body: JSON.stringify({
      model: process.env.FOUNDRY_ROUTER_MODEL || "auto",
      routing_config: { mode, session_affinity: { strategy: "none" } },
      messages: [{ role: "user", content: prompt }],
      max_completion_tokens: 160,
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Foundry router returned HTTP ${res.status}: ${body}`);
  }
  return await res.json();
}

export async function tryLiveDecisionCall(state, questions) {
  const endpoint = process.env.AZURE_FOUNDRY_ENDPOINT?.replace(/\/+$/, "");
  const deployment = process.env.DECISION_DEPLOYMENT;
  if (!endpoint || !deployment) return null;
  const auth = getBearerToken();
  if (!auth) return null;

  const res = await fetch(`${endpoint}/providers/microsoft/v1/systemone`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [auth.headerName]: auth.headerValue,
    },
    body: JSON.stringify({ model: deployment, state, questions }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Decision-1.1 returned HTTP ${res.status}: ${body}`);
  }
  return await res.json();
}

async function replayDemo(recordings, kind) {
  const steps = recordings.steps[kind];
  if (!steps) throw new Error(`Unknown demo kind: ${kind}`);
  console.log(`\n============================================================`);
  console.log(`  AUTO-ROUTING DEMO: ${kind.toUpperCase()}`);
  console.log(`============================================================`);
  for (const stepKey of Object.keys(steps).sort((a, b) => Number(a) - Number(b))) {
    console.log(`\n--- Step ${stepKey} ---`);
    for (const item of steps[stepKey]) {
      if (item.event.kind === "output") {
        process.stdout.write(item.event.text);
      }
    }
  }
}

async function main() {
  const { demo, live } = parseArgs(process.argv.slice(2));
  const recordings = JSON.parse(await readFile(recordingsPath, "utf8"));

  if (live && process.env.AZURE_FOUNDRY_ENDPOINT && (demo === "foundry" || demo === "all")) {
    console.log("[Live Mode] Querying Microsoft Foundry Model Router (`model: auto`)...");
    const liveRes = await tryLiveFoundryRoute(
      "Extract invoice ID and currency as JSON from: Invoice INV-2026-8841, Total 4,250 EUR.",
      "balanced",
    );
    if (liveRes) {
      console.log("Live served model:", liveRes.model);
      console.log("Live routing_trace:", JSON.stringify(liveRes.model_selection_details?.model_router_details, null, 2));
    }
  }

  const targets = demo === "all" ? ["fusion", "foundry", "decision"] : [demo];
  for (const k of targets) {
    await replayDemo(recordings, k);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
