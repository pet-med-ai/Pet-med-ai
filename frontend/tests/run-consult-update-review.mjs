import { build } from "esbuild";
import { mkdtemp, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
// Keep the transient bundle under frontend so external packages resolve normally.
const temporary = await mkdtemp(join(root, ".consult-update-test-"));
try {
  const names = ["consult-update-review", "consult-first-save", "consult-draft", "case-edit-review", "manual-case-create"];
  const outputs = names.map(name => join(temporary, name + ".cjs"));
  for (let index = 0; index < names.length; index++) {
    await build({
      entryPoints: [join(root, "tests", names[index] + ".test.jsx")], outfile: outputs[index],
      bundle: true, platform: "node", format: "cjs", packages: "external",
      define: { "import.meta.env": "{}" }, logLevel: "warning",
    });
  }
  const result = spawnSync(process.execPath, ["--test", ...outputs], { stdio: "inherit" });
  process.exitCode = result.status ?? 1;
} finally {
  await rm(temporary, { recursive: true, force: true });
}
