import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { chromium, type Browser } from "playwright-core";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const BROWSER_CANDIDATES = [
  process.env.PDF_BROWSER_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].filter((value): value is string => Boolean(value));

function sanitizeFilename(filename: string) {
  const trimmed = filename.trim() || "analysis-report.pdf";
  const normalized = trimmed.toLowerCase().endsWith(".pdf") ? trimmed : `${trimmed}.pdf`;
  return normalized.replace(/[^a-zA-Z0-9._-]/g, "_");
}

async function resolveBrowserExecutable() {
  for (const candidate of BROWSER_CANDIDATES) {
    try {
      await access(candidate, constants.F_OK);
      return candidate;
    } catch {
      // Try the next installed browser path.
    }
  }

  throw new Error(
    "No supported Chrome or Edge installation was found for PDF export."
  );
}

export async function POST(request: NextRequest) {
  let browser: Browser | undefined;

  try {
    const body = (await request.json()) as {
      filename?: string;
      html?: string;
      viewportWidth?: number;
    };

    if (!body.html) {
      return NextResponse.json(
        { error: "Missing report HTML for PDF export." },
        { status: 400 }
      );
    }

    const executablePath = await resolveBrowserExecutable();
    browser = await chromium.launch({
      headless: true,
      executablePath,
      args: ["--disable-gpu", "--no-sandbox"],
    });

    const page = await browser.newPage({
      viewport: {
        width: Math.max(1024, Math.min(Math.floor(body.viewportWidth || 1280), 1800)),
        height: 2200,
      },
    });

    await page.emulateMedia({ media: "screen" });
    await page.setContent(body.html, { waitUntil: "load" });
    await page.waitForLoadState("networkidle").catch(() => undefined);
    await page.evaluate(async () => {
      if ("fonts" in document) {
        await document.fonts.ready;
      }
    });

    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: {
        top: "15mm",
        right: "10mm",
        bottom: "15mm",
        left: "10mm",
      },
      preferCSSPageSize: false,
    });

    return new NextResponse(Buffer.from(pdfBuffer), {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${sanitizeFilename(
          body.filename || "analysis-report.pdf"
        )}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unexpected PDF export error.";

    return NextResponse.json({ error: message }, { status: 500 });
  } finally {
    await browser?.close();
  }
}
