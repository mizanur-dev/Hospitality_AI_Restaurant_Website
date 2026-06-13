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
      args: [
        "--disable-gpu",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        // Force a predictable DPI so layout calculations are stable
        "--force-device-scale-factor=1",
      ],
    });

    /*
     * Viewport width strategy:
     * ─────────────────────────────────────────────────────────────────────────
     * A4 at 96 dpi = 794 px wide.  We use 800 px so that responsive CSS
     * breakpoints fire at ≤ 768 px (md) and ≤ 1024 px (lg) correctly.
     * This prevents content from being squished as it was at 1280 px, and
     * matches the print CSS @page margins (~760 px usable).
     *
     * The height is set generously (10 000 px) so Playwright never clips
     * the document – Chromium renders the full page before pagination.
     * ─────────────────────────────────────────────────────────────────────────
     */
    const viewportWidth = 800; // A4-equivalent viewport — do not change to 1280
    const page = await browser.newPage({
      viewport: {
        width: viewportWidth,
        height: 10000,
      },
    });

    /*
     * Use "screen" media so the inlined computed styles (captured from the
     * live light-mode screen) render exactly as they appeared in the browser.
     * Playwright's page.pdf() handles print pagination independently of the
     * emulated media type.  The page-break rules are already in the inlined
     * PDF_PRINT_CSS block and do not depend on @media print to activate.
     */
    await page.emulateMedia({ media: "screen" });
    await page.setContent(body.html, { waitUntil: "domcontentloaded" });

    // Wait for network to settle (images, fonts from CDN, etc.)
    await page.waitForLoadState("networkidle").catch(() => undefined);

    // Wait for all web fonts to be ready before rendering
    await page.evaluate(async () => {
      if ("fonts" in document) {
        await (document as Document & { fonts: FontFaceSet }).fonts.ready;
      }
    });

    // Give any deferred JS renders (e.g. Recharts SVG) a moment to complete
    await page.waitForTimeout(500);

    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      /*
       * Page margins in mm – must match the @page margin in pdf-print.css
       * (15 mm top/bottom, 12 mm left/right).
       */
      margin: {
        top: "15mm",
        right: "12mm",
        bottom: "15mm",
        left: "12mm",
      },
      /*
       * preferCSSPageSize: false lets Playwright override the @page size
       * with the format:"A4" value above, which is more reliable across
       * Chromium versions.
       */
      preferCSSPageSize: false,
      /*
       * displayHeaderFooter: false removes the default Chromium header that
       * includes the URL and date, keeping pages clean.
       */
      displayHeaderFooter: false,
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
