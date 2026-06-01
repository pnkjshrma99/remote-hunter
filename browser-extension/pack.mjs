/* ────────────────────────────────────────────
   Packing script for browser extension.
   Usage:  node pack.mjs
   Output: packaged/remote-hunter-autofill.zip   (Edge / Chrome Web Store)
           packaged/remote-hunter-autofill.zip   (same file, works on both)
   ──────────────────────────────────────────── */

import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dist = join(__dirname, "dist");
const outDir = join(__dirname, "packaged");

// 1. Build
console.log("→ Building extension...");
execSync("node build.mjs", { cwd: __dirname, stdio: "inherit" });

// 2. Generate icons if missing
console.log("→ Ensuring icons...");
const iconSizes = [16, 48, 128];
for (const s of iconSizes) {
  const p = join(dist, `icon-${s}.png`);
  if (existsSync(p)) {
    console.log(`  ✓ icon-${s}.png`);
  } else {
    console.warn(`  ! icon-${s}.png missing — run the Python icon generator.`);
  }
}

// 3. Create packaged/ directory
if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

// 4. Create ZIP with files at root level (not inside a subfolder)
const zipName = "remote-hunter-autofill.zip";
const zipPath = join(outDir, zipName);

// Remove old zip if exists
if (existsSync(zipPath)) {
  execSync(`rm "${zipPath}"`, { stdio: "ignore" });
}

const keep = [
  "manifest.json",
  "background.js",
  "content.js",
  "autofill-inject.js",
  "popup.html",
  "popup.css",
  "popup.js",
  ...iconSizes.map((s) => `icon-${s}.png`),
];

// Zip files directly — no subfolder
execSync(
  `cd "${dist}" && zip -r "${zipPath}" ${keep.join(" ")} -x "*.DS_Store"`,
  { stdio: "inherit" }
);

const sizeKb = (statSync(zipPath).size / 1024).toFixed(1);

console.log(`\n✓ Packaged: ${zipPath} (${sizeKb} KB)`);
console.log("");
console.log("  ── How to publish ──");
console.log("  Edge Add-ons (free):");
console.log("    1. Go to https://partner.microsoft.com/dashboard/microsoftedge/overview");
console.log("    2. Sign in (free Microsoft account)");
console.log("    3. Create a new extension submission");
console.log("    4. Upload this zip, fill details, submit");
console.log("    5. Set NEXT_PUBLIC_EDGE_EXTENSION_URL to the published URL");
console.log("");
console.log("  Chrome Web Store ($5):");
console.log("    1. Go to https://chrome.google.com/webstore/devconsole");
console.log("    2. Pay the one-time $5 registration fee");
console.log("    3. Upload this zip, fill details, submit");
console.log("    4. Set NEXT_PUBLIC_EXTENSION_STORE_URL to the published URL");
