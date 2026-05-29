import { NextResponse } from "next/server";
import { existsSync, mkdirSync, readFileSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";

export async function GET() {
  const extDir = join(process.cwd(), "..", "browser-extension");
  const distDir = join(extDir, "dist");

  // Auto-build if dist doesn't exist
  if (!existsSync(distDir)) {
    try {
      execSync("node build.mjs", { cwd: extDir, stdio: "pipe" });
    } catch {
      return new NextResponse("Failed to build extension", { status: 500 });
    }
  }

  // Create a temp zip using the system zip command
  const tmpDir = join(extDir, ".tmp-zip");
  const staging = join(tmpDir, "remote-hunter-autofill");
  const zipPath = join(tmpDir, "remote-hunter-autofill.zip");

  if (!existsSync(tmpDir)) mkdirSync(tmpDir, { recursive: true });

  // Remove stale files
  execSync(`rm -rf "${staging}" "${zipPath}"`, { stdio: "ignore" });

  // Copy dist files into staging
  execSync(`mkdir -p "${staging}" && cp -R "${distDir}/" "${staging}/"`, { stdio: "ignore" });

  // Create zip
  execSync(`cd "${tmpDir}" && zip -r "remote-hunter-autofill.zip" "remote-hunter-autofill" -x "*.DS_Store"`, { stdio: "pipe" });

  const zip = readFileSync(zipPath);

  // Cleanup
  execSync(`rm -rf "${tmpDir}"`, { stdio: "ignore" });

  return new NextResponse(zip, {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition":
        'attachment; filename="remote-hunter-autofill.zip"',
    },
  });
}
