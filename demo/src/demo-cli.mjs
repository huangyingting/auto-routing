#!/usr/bin/env node
/**
 * CLI runner for the three Auto-Routing LLMs demos:
 *   1. fusion   - GitHub Copilot CLI Auto (HyDRA) & Multi-Model Cascade / Critique / Prefix Cache
 *   2. foundry  - Microsoft Foundry Model Router (/openai/v1/chat/completions + live HTTP 429->200 failover)
 *   3. decision - Microsoft-Decision-1.1 (/providers/microsoft/v1/systemone: choice, score, noul)
 *
 * Modes:
 *   Default  : Executes LIVE automatically whenever the required CLI / cloud endpoint is available
 *              (Copilot CLI for `fusion` & Step 5 local HTTP failover work out-of-the-box;
 *               Foundry Steps 1–4 & Decision-1.1 Steps 1–5 run live when AZURE_FOUNDRY_ENDPOINT is set).
 *   --live   : Strict live mode — never falls back to recorded traces; exits non-zero if prerequisites are missing.
 *   --replay : Plays verified pre-recorded traces from presentation/assets/demo-recordings.json.
 *   --step N : Runs only step N (1..5) of the selected demo.
 *   --probe  : Routes an arbitrary custom prompt live via Decision-1.1 or Copilot CLI Auto.
 */
import { readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  callDecisionSystemOne,
  callFoundryRouter,
  detectLiveCapabilities,
  probeCustomPromptLive,
  runDecisionStepLive,
  runFoundryStepLive,
  runFusionStepLive,
} from "./live-runners.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");
const recordingsPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");

function parseArgs(argv) {
  let demo = "all";
  let mode = "auto";
  let step = null;
  let probe = null;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--demo" && argv[i + 1]) {
      demo = argv[i + 1];
      i += 1;
    } else if (arg === "--step" && argv[i + 1]) {
      step = Number.parseInt(argv[i + 1], 10);
      i += 1;
    } else if (arg === "--probe" && argv[i + 1]) {
      probe = argv[i + 1];
      i += 1;
    } else if (arg === "--live") {
      mode = "live";
    } else if (arg === "--replay") {
      mode = "replay";
    }
  }
  return { demo, mode, step, probe };
}

export async function tryLiveFoundryRoute(prompt, mode = "balanced") {
  const { json } = await callFoundryRouter({
    messages: [{ role: "user", content: prompt }],
    mode,
  });
  return json;
}

export async function tryLiveDecisionCall(state, questions) {
  const { json } = await callDecisionSystemOne({ state, questions });
  return json;
}

function cliEmitter(event) {
  if (event.kind === "step-start") {
    console.log(`\n--- [${event.demo.toUpperCase()} · Step ${event.step}] ---`);
  } else if (event.kind === "output") {
    process.stdout.write(event.text);
  }
}

async function replayStep(recordings, kind, stepNum, reason = null) {
  const seq = recordings.steps?.[kind]?.[String(stepNum)];
  if (!seq) throw new Error(`Unknown demo=${kind} step=${stepNum}`);
  console.log(`\n--- [${kind.toUpperCase()} · Step ${stepNum} (Replay)] ---`);
  if (reason) {
    console.log(`  [Note] ${reason}`);
  }
  for (const item of seq) {
    if (item.event.kind === "output") {
      process.stdout.write(item.event.text);
    }
  }
}

async function runTargetDemo(kind, stepsToRun, mode, caps, recordings, sessionStore) {
  console.log(`\n============================================================`);
  console.log(`  AUTO-ROUTING DEMO: ${kind.toUpperCase()}  (mode: ${mode.toUpperCase()})`);
  console.log(`============================================================`);

  for (const s of stepsToRun) {
    if (mode === "replay") {
      await replayStep(recordings, kind, s);
      continue;
    }

    if (kind === "fusion") {
      if (!caps.copilotAvailable) {
        if (mode === "live") {
          throw new Error(
            "Live `fusion` demo requires GitHub Copilot CLI (`copilot`) on PATH and signed in (`copilot login`).",
          );
        }
        await replayStep(recordings, kind, s, "GitHub Copilot CLI not detected -> using verified replay.");
        continue;
      }
      await runFusionStepLive(s, cliEmitter, sessionStore);
      continue;
    }

    if (kind === "foundry") {
      if (s === 5) {
        await runFoundryStepLive(5, cliEmitter);
        continue;
      }
      if (!caps.foundryReady) {
        if (mode === "live") {
          throw new Error(
            "Live `foundry` Steps 1–4 require AZURE_FOUNDRY_ENDPOINT plus AZURE_FOUNDRY_API_KEY, AZURE_ENTRA_TOKEN, or `az login`.",
          );
        }
        await replayStep(
          recordings,
          kind,
          s,
          "AZURE_FOUNDRY_ENDPOINT not set -> using verified replay (set AZURE_FOUNDRY_ENDPOINT for live cloud calls).",
        );
        continue;
      }
      await runFoundryStepLive(s, cliEmitter);
      continue;
    }

    if (kind === "decision") {
      if (!caps.decisionReady) {
        if (mode === "live") {
          throw new Error(
            "Live `decision` demo requires AZURE_FOUNDRY_ENDPOINT (and optional DECISION_DEPLOYMENT, default 'microsoft-decision-1.1') plus AZURE_FOUNDRY_API_KEY, AZURE_ENTRA_TOKEN, or `az login`.",
          );
        }
        await replayStep(
          recordings,
          kind,
          s,
          "AZURE_FOUNDRY_ENDPOINT not set -> using verified replay (set AZURE_FOUNDRY_ENDPOINT for live /v1/systemone calls).",
        );
        continue;
      }
      await runDecisionStepLive(s, cliEmitter);
      continue;
    }

    throw new Error(`Unknown demo kind: ${kind}`);
  }
}

async function main() {
  const { demo, mode, step, probe } = parseArgs(process.argv.slice(2));
  const caps = detectLiveCapabilities();

  if (probe) {
    const res = await probeCustomPromptLive(probe);
    if (!res) {
      throw new Error("Live probe requires either GitHub Copilot CLI (`copilot`) or AZURE_FOUNDRY_ENDPOINT.");
    }
    console.log(`[${res.source}]`);
    console.log(`  Selected : ${res.model} (${res.meta})`);
    console.log(`  Summary  : ${res.summary}`);
    return;
  }

  const recordings = JSON.parse(await readFile(recordingsPath, "utf8"));
  const targets = demo === "all" ? ["fusion", "foundry", "decision"] : [demo];
  const stepsToRun = step ? [step] : [1, 2, 3, 4, 5];
  const sessionStore = {};

  try {
    for (const k of targets) {
      await runTargetDemo(k, stepsToRun, mode, caps, recordings, sessionStore);
    }
  } finally {
    if (sessionStore.fusionDir) {
      await rm(sessionStore.fusionDir, { recursive: true, force: true }).catch(() => {});
    }
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    console.error(`\n[Demo Error] ${err.message || err}`);
    process.exit(1);
  });
}
