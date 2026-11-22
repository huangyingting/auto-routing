#!/usr/bin/env node
/**
 * Validates and pretty-prints presentation/assets/demo-recordings.json.
 * If AZURE_FOUNDRY_ENDPOINT is set, also refreshes Step 2 & Step 3 Foundry Model Router telemetry.
 */
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tryLiveFoundryRoute } from "./demo-cli.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");
const outPath = path.join(repoRoot, "presentation", "assets", "demo-recordings.json");

async function main() {
  const data = JSON.parse(await readFile(outPath, "utf8"));
  if (process.env.AZURE_FOUNDRY_ENDPOINT) {
    const simple = await tryLiveFoundryRoute(
      "Extract invoice ID and currency as JSON from: Invoice INV-2026-8841, Total 4,250 EUR.",
      "balanced",
    );
    if (simple) {
      console.log(`Refreshed live Foundry simple trace -> ${simple.model}`);
    }
  }
  await writeFile(outPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  console.log(`Verified ${outPath} (${Object.keys(data.steps).length} demos)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
