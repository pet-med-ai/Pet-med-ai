import { build } from "esbuild";
import { mkdtemp, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
// Keep the transient bundle under frontend so external packages resolve normally.
const temporary = await mkdtemp(join(root, ".consult-update-test-"));
try {
  const outfile = join(temporary, "tests.cjs");
  await build({
    entryPoints: [join(root, "tests/consult-update-review.test.jsx")], outfile,
    bundle: true, platform: "node", format: "cjs", packages: "external",
    define: { "import.meta.env": "{}" }, logLevel: "warning",
  });
  const result = spawnSync(process.execPath, ["--test", outfile], { stdio: "inherit" });
  process.exitCode = result.status ?? 1;
} finally {
  await rm(temporary, { recursive: true, force: true });
}
