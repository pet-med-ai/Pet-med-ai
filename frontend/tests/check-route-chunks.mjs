// Run after `npm run build -- --manifest`; inspect artifacts without serving or calling APIs.
import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const frontend = dirname(dirname(fileURLToPath(import.meta.url)));
const dist = resolve(process.argv[2] || resolve(frontend, "dist"));
const manifest = JSON.parse(await readFile(resolve(dist, ".vite/manifest.json"), "utf8"));
const entry = Object.keys(manifest).find(key => manifest[key].isEntry && manifest[key].src === "index.html");
assert(entry, "Missing application entry in Vite manifest");
const eager = new Set();
function walk(key) {
  assert(manifest[key], `Missing manifest entry: ${key}`);
  if (eager.has(key)) return;
  eager.add(key);
  for (const dependency of manifest[key].imports || []) walk(dependency);
}
walk(entry);
const deferred = [
  "KpiDashboard", "WebhookInboxPage", "EmrImportBatchPlanningPage", "OpsDashboard",
  "PreventiveCareNotificationQueuePage", "AutomatedReminderDeliveryManualApprovalPage",
].map(name => `src/pages/${name}.jsx`);
for (const key of deferred) {
  assert(manifest[key]?.isDynamicEntry, `Page must remain on demand: ${key}`);
  assert(manifest[entry].dynamicImports?.includes(key), `Missing lazy route import: ${key}`);
  assert(!eager.has(key), `Page unexpectedly loaded with home: ${key}`);
  assert((await stat(resolve(dist, manifest[key].file))).size > 0, `Missing route asset: ${key}`);
}
const chunks = Object.values(manifest).filter(item => item.file.endsWith(".js"));
const files = [...new Set(chunks.map(item => item.file))];
for (const file of files) {
  const size = (await stat(resolve(dist, file))).size;
  assert(size <= 500_000, `JavaScript chunk exceeds 500 kB: ${file} (${size})`);
}
const initialFiles = [...new Set([...eager].map(key => manifest[key].file))];
let initialBytes = 0, initialGzipBytes = 0;
for (const file of initialFiles) {
  const bytes = await readFile(resolve(dist, file));
  initialBytes += bytes.length;
  initialGzipBytes += gzipSync(bytes).length;
}
// Include all eagerly imported chunks, so vendor splitting cannot hide excess initial payload.
assert(initialBytes <= 460_000, `Initial JS exceeds the reviewed 460 kB budget: ${initialBytes}`);
const html = await readFile(resolve(dist, "index.html"), "utf8");
for (const key of deferred) {
  assert(!html.includes(manifest[key].file), `Deferred route preloaded by index.html: ${key}`);
}
console.log(JSON.stringify({ status: "PASS", initialBytes, initialGzipBytes, initialFiles, deferredRoutes: deferred.length, jsFiles: files.length }, null, 2));
