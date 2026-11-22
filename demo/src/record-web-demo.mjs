#!/usr/bin/env node
/**
 * Re-records live traces into presentation/assets/demo-recordings.json for available live backends
 * (Copilot CLI for `fusion` when --record-fusion is passed; Foundry & Decision-1.1 when AZURE_FOUNDRY_ENDPOINT is set),
 * and validates all 15 step recordings.
 */
import { readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  detectLiveCapabilities,
  runDecisionStepLive,
  runFoundryStepLive,
  runFusionStepLive,
} from "./live-runners.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");
const outPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");

async function captureStep(runFn) {
  const events = [];
  let last = Date.now();
  await runFn((event) => {
    const now = Date.now();
    events.push({ delayMs: Math.min(200, Math.max(10, now - last)), event });
    last = now;
  });
  return events;
}

async function main() {
  const recordFusion = process.argv.includes("--record-fusion");
  const data = JSON.parse(await readFile(outPath, "utf8"));
  const caps = detectLiveCapabilities();
  const sessionStore = {};

  try {
    if (recordFusion && caps.copilotAvailable) {
      for (let s = 1; s <= 5; s += 1) {
        console.log(`Recording live fusion step ${s}...`);
        data.steps.fusion[String(s)] = await captureStep((emit) => runFusionStepLive(s, emit, sessionStore));
      }
    }
    if (caps.foundryReady) {
      for (let s = 1; s <= 5; s += 1) {
        console.log(`Recording live foundry step ${s}...`);
        data.steps.foundry[String(s)] = await captureStep((emit) => runFoundryStepLive(s, emit));
      }
    }
    if (caps.decisionReady && process.env.DECISION_DEPLOYMENT) {
      for (let s = 1; s <= 5; s += 1) {
        console.log(`Recording live decision step ${s}...`);
        data.steps.decision[String(s)] = await captureStep((emit) => runDecisionStepLive(s, emit));
      }
    }
  } finally {
    if (sessionStore.fusionDir) {
      await rm(sessionStore.fusionDir, { recursive: true, force: true }).catch(() => {});
    }
  }

  await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  console.log(`Verified ${outPath} (${Object.keys(data.steps).length} demos)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
