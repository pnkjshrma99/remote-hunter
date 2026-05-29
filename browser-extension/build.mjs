import * as esbuild from "esbuild";
import { copyFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dist = join(__dirname, "dist");

if (!existsSync(dist)) mkdirSync(dist, { recursive: true });

const entries = [
  "src/background.ts",
  "src/content.ts",
  "src/popup.ts",
  "src/autofill-inject.ts",
];

await esbuild.build({
  entryPoints: entries.map((e) => join(__dirname, e)),
  outdir: dist,
  bundle: true,
  format: "iife",
  platform: "browser",
  target: "es2020",
  minify: false,
  sourcemap: false,
});

["manifest.json", "src/popup.html", "src/popup.css"].forEach((file) => {
  copyFileSync(join(__dirname, file), join(dist, file === "src/popup.html" ? "popup.html" : file === "src/popup.css" ? "popup.css" : file));
});

console.log("✓ Extension built to dist/");
