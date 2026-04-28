const { execFileSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
const nextBin = require.resolve("next/dist/bin/next");
const suppressedPattern = /\[baseline-browser-mapping\].*over two months old/i;
const projectRoot = path.resolve(__dirname, "..");
const lockFile = path.join(projectRoot, ".next", "dev", "lock");
let child;

function cleanupExistingDevProcesses() {
  if (args[0] !== "dev") {
    return;
  }

  if (process.platform === "win32") {
    const escapedRoot = projectRoot.replace(/'/g, "''").toLowerCase();
    const powershellScript = [
      `$project = '${escapedRoot}'`,
      `$currentPid = ${process.pid}`,
      "$targets = Get-CimInstance Win32_Process | Where-Object {",
      "  $_.Name -eq 'node.exe' -and",
      "  $_.ProcessId -ne $currentPid -and",
      "  $_.CommandLine -and",
      "  $_.CommandLine.ToLower().Contains($project) -and",
      "  (",
      "    $_.CommandLine -like '*scripts/run-next.cjs dev*' -or",
      "    $_.CommandLine -like '*next\\dist\\bin\\next* dev*' -or",
      "    $_.CommandLine -like '*next/dist/bin/next* dev*'",
      "  )",
      "} | Sort-Object ProcessId -Descending",
      "foreach ($proc in $targets) {",
      "  Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue",
      "}",
    ].join(" ");

    try {
      execFileSync(
        "powershell.exe",
        ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershellScript],
        { stdio: "ignore" }
      );
    } catch {
      // If cleanup fails, Next.js can still surface the underlying error.
    }
  }

  try {
    fs.rmSync(lockFile, { force: true });
  } catch {
    // Ignore stale lock cleanup errors.
  }
}

cleanupExistingDevProcesses();

function pipeFiltered(stream, destination) {
  let buffer = "";

  stream.on("data", (chunk) => {
    buffer += chunk.toString();
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!suppressedPattern.test(line)) {
        destination.write(`${line}\n`);
      }
    }
  });

  stream.on("end", () => {
    if (buffer && !suppressedPattern.test(buffer)) {
      destination.write(buffer);
    }
  });
}

function killChildTree() {
  if (!child || child.killed) {
    return;
  }

  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } else {
      child.kill("SIGTERM");
    }
  } catch {
    // Ignore cleanup errors during shutdown.
  }
}

child = spawn(process.execPath, [nextBin, ...args], {
  cwd: path.resolve(__dirname, ".."),
  env: {
    ...process.env,
    BASELINE_BROWSER_MAPPING_IGNORE_OLD_DATA: "true",
    BROWSERSLIST_IGNORE_OLD_DATA: "true",
  },
  stdio: ["inherit", "pipe", "pipe"],
});

pipeFiltered(child.stdout, process.stdout);
pipeFiltered(child.stderr, process.stderr);

["SIGINT", "SIGTERM", "SIGHUP"].forEach((signal) => {
  process.on(signal, () => {
    killChildTree();
    process.exit(0);
  });
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
