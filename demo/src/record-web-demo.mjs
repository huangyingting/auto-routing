#!/usr/bin/env node
/**
 * Re-records live traces into presentation/assets/demo-recordings.json for available live backends
 * (Copilot CLI for `fusion` when --record-fusion is passed; Foundry & Decision-1.1 when AZURE_FOUNDRY_ENDPOINT is set),
 * and validates all 13 scenario recordings.
 * Use --decision-only --steps 1 to refresh only Decision-1.1 Step 1.
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

function sanitizeString(str) {
  if (typeof str !== "string") return str;
  let out = str;
  if (process.env.AZURE_FOUNDRY_ENDPOINT) {
    const ep = process.env.AZURE_FOUNDRY_ENDPOINT.replace(/\/+$/, "");
    out = out.split(ep).join("https://<foundry-resource>.cognitiveservices.azure.com");
  }
  out = out.replace(/[A-Za-z]:\\+Users\\+[^"\\\s]+\\+AppData\\+Local\\+Temp\\+/g, (m) => {
    const sep = m.includes("\\\\\\\\") ? "\\\\\\\\" : "\\\\";
    return `<temp-workspace>${sep}`;
  });
  out = out.replace(/[A-Za-z]:\\+Users\\+[^"\\\s]+\\+\.copilot\\+/g, (m) => {
    const sep = m.includes("\\\\\\\\") ? "\\\\\\\\" : "\\\\";
    return `<user-home>${sep}.copilot${sep}`;
  });
  return out;
}

function sanitizeEvents(events) {
  return JSON.parse(sanitizeString(JSON.stringify(events)));
}

async function captureStep(runFn) {
  const events = [];
  let last = Date.now();
  await runFn((event) => {
    const now = Date.now();
    events.push({ delayMs: Math.min(160, Math.max(15, now - last)), event });
    last = now;
  });
  return sanitizeEvents(events);
}

async function main() {
  const recordFusion = process.argv.includes("--record-fusion") || process.argv.includes("--fusion-only");
  const fusionOnly = process.argv.includes("--fusion-only");
  const decisionOnly = process.argv.includes("--decision-only");
  const data = JSON.parse(await readFile(outPath, "utf8"));
  const caps = detectLiveCapabilities();
  const sessionStore = {};

  data.platform = "win32/x64 · Live-captured Copilot CLI 1.0.115-7 (--model auto & --model fusion --fusion-tier high) + Microsoft Foundry Model Router V1Preview + Microsoft-Decision-1.1";

  const stepsIdx = process.argv.indexOf("--steps");
  const requestedSteps = stepsIdx >= 0 && process.argv[stepsIdx + 1]
    ? process.argv[stepsIdx + 1].split(",").map((x) => Number.parseInt(x, 10)).filter(Boolean)
    : null;
  const fusionSteps = requestedSteps || [1, 2, 3, 4];

  try {
    if (recordFusion && caps.copilotAvailable) {
      delete data.steps.fusion["5"];
      for (const s of fusionSteps) {
        console.log(`Recording live fusion step ${s}...`);
        data.steps.fusion[String(s)] = await captureStep((emit) => runFusionStepLive(s, emit, sessionStore));
        await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
      }
    }
    if (!fusionOnly && !decisionOnly && caps.foundryReady) {
      delete data.steps.foundry["5"];
      for (let s = 1; s <= 4; s += 1) {
        console.log(`Recording live foundry step ${s}...`);
        data.steps.foundry[String(s)] = await captureStep((emit) => runFoundryStepLive(s, emit));
        await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
      }
    }
    if (!fusionOnly && caps.decisionReady) {
      const decisionSteps = decisionOnly && requestedSteps ? requestedSteps : [1, 2, 3, 4, 5];
      delete data.steps.decision["5"];
      for (const s of decisionSteps) {
        console.log(`Recording live decision step ${s}...`);
        data.steps.decision[String(s)] = await captureStep((emit) => runDecisionStepLive(s, emit));
        await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
      }
    }
  } finally {
    for (const key of ["fusionDir", "autoDir"]) {
      if (sessionStore[key]) {
        await rm(sessionStore[key], { recursive: true, force: true }).catch(() => {});
      }
    }
  }

  await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  console.log(`Verified ${outPath} (${Object.keys(data.steps).length} demos)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
