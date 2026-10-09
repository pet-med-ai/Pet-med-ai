import { build } from "esbuild";
import { mkdtemp, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
// Keep the transient bundle under frontend so external packages resolve normally.
const temporary = await mkdtemp(join(root, ".consult-update-test-"));
try {
  const names = ["consult-update-review", "consult-first-save", "consult-draft", "case-edit-review", "manual-case-create", "case-list-auth", "case-detail-documents", "deferred-pages", "diarrhea-intake", "chief-complaint-intake", "consult-evidence", "voice-draft", "audio-capture", "case-attachments", "manual-lab-results", "manual-lab-documents", "manual-imaging-records", "manual-imaging-documents", "visit-overview", "case-detail-overview", "lab-range-review", "case-detail-lab-range-review", "lab-comparison", "case-detail-lab-comparison", "lab-comparison-documents", "case-detail-lab-comparison-documents", "followup-plan", "case-detail-followup-plan"];
  names.push('followup-plan-documents', 'case-detail-followup-plan-documents');
  names.push('followup-plan-owner-documents', 'case-detail-followup-plan-owner-documents');
  names.push('followup-plan-overview', 'case-detail-followup-plan-overview');
  names.push('followup-plan-queue', 'case-detail-followup-plan-queue');
  names.push('followup-contacts', 'case-detail-followup-contacts');
  names.push('followup-contact-overview', 'case-detail-followup-contact-overview');
  names.push('followup-contact-documents', 'case-detail-followup-contact-documents');
  names.push('followup-contact-owner-documents', 'case-detail-followup-contact-owner-documents');
  const outputs = names.map(name => join(temporary, name + ".cjs"));
  for (let index = 0; index < names.length; index++) {
    await build({
      entryPoints: [join(root, "tests", names[index] + ".test.jsx")], outfile: outputs[index],
      bundle: true, platform: "node", format: "cjs", packages: "external",
      define: { "import.meta.env": "{}", "import.meta.url": JSON.stringify(import.meta.url) }, logLevel: "warning",
    });
  }
  const result = spawnSync(process.execPath, ["--test", "--test-concurrency=2", ...outputs], { stdio: "inherit" });
  process.exitCode = result.status ?? 1;
} finally {
  await rm(temporary, { recursive: true, force: true });
}
