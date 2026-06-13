"use client";

interface PdfExportPayload {
  filename: string;
  html: string;
  viewportWidth: number;
}

/**
 * CSS properties that are irrelevant for a printed PDF and would only bloat
 * the inline style strings.  Skipping them keeps the HTML payload smaller.
 */
const STYLE_PROPERTIES_TO_SKIP = new Set([
  "animation",
  "animation-delay",
  "animation-direction",
  "animation-duration",
  "animation-fill-mode",
  "animation-iteration-count",
  "animation-name",
  "animation-play-state",
  "animation-timing-function",
  "caret-color",
  "cursor",
  "perspective-origin",
  "pointer-events",
  "scroll-behavior",
  "transition",
  "transition-delay",
  "transition-duration",
  "transition-property",
  "transition-timing-function",
  "user-select",
]);

function isIgnoredForPdf(node: Element) {
  return (
    node.hasAttribute("data-pdf-export-ignore") ||
    node.hasAttribute("data-html2canvas-ignore")
  );
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function collectHeadMarkup(doc: Document) {
  return Array.from(doc.head.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((node) => {
      if (node instanceof HTMLLinkElement) {
        return `<link rel="stylesheet" href="${escapeHtml(node.href)}" />`;
      }

      return node.outerHTML;
    })
    .join("\n");
}

function replaceCanvasWithImages(sourceRoot: HTMLElement, clonedRoot: HTMLElement) {
  const sourceCanvases = Array.from(sourceRoot.querySelectorAll("canvas"));
  const clonedCanvases = Array.from(clonedRoot.querySelectorAll("canvas"));

  sourceCanvases.forEach((sourceCanvas, index) => {
    const clonedCanvas = clonedCanvases[index];
    if (!clonedCanvas) return;

    try {
      const image = document.createElement("img");
      image.src = sourceCanvas.toDataURL("image/png");
      image.alt = sourceCanvas.getAttribute("aria-label") || "Chart";
      image.setAttribute("data-pdf-chart", "true");
      image.style.display = "block";
      image.style.width = `${sourceCanvas.clientWidth || sourceCanvas.width}px`;
      image.style.maxWidth = "100%";
      image.style.height = "auto";
      // Keep chart images together on the same page
      image.style.breakInside = "avoid";
      image.style.pageBreakInside = "avoid";
      clonedCanvas.replaceWith(image);
    } catch {
      // If a canvas cannot be serialized, keep the original node in place.
    }
  });
}

/**
 * Walk the element tree, respecting data-pdf-export-ignore markers.
 * Returns a flat list of HTMLElements in document order.
 */
function getExportableElements(root: HTMLElement) {
  const elements: HTMLElement[] = [];

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, {
    acceptNode: (node) => {
      if (!(node instanceof HTMLElement)) {
        return NodeFilter.FILTER_SKIP;
      }

      return isIgnoredForPdf(node)
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT;
    },
  });

  const currentRoot = walker.currentNode;
  if (currentRoot instanceof HTMLElement && !isIgnoredForPdf(currentRoot)) {
    elements.push(currentRoot);
  }

  while (walker.nextNode()) {
    const current = walker.currentNode;
    if (current instanceof HTMLElement) {
      elements.push(current);
    }
  }

  return elements;
}

/**
 * Copy the computed styles from the live DOM onto the cloned elements.
 *
 * This is the critical function that makes PDF output match the screen.
 * Without it, Playwright's isolated browser context cannot resolve CSS module
 * class names or reach the Next.js dev-server stylesheets, resulting in
 * completely unstyled output.
 */
function inlineComputedStyles(sourceRoot: HTMLElement, clonedRoot: HTMLElement) {
  const sourceElements = getExportableElements(sourceRoot);
  const clonedElements = getExportableElements(clonedRoot);

  sourceElements.forEach((sourceElement, index) => {
    const clonedElement = clonedElements[index];
    if (!clonedElement) return;

    const computedStyle = window.getComputedStyle(sourceElement);

    for (const propertyName of Array.from(computedStyle)) {
      if (STYLE_PROPERTIES_TO_SKIP.has(propertyName)) continue;

      const propertyValue = computedStyle.getPropertyValue(propertyName);
      if (!propertyValue) continue;

      clonedElement.style.setProperty(
        propertyName,
        propertyValue,
        computedStyle.getPropertyPriority(propertyName)
      );
    }
  });
}

/**
 * Add page-break-avoidance classes to the cloned element tree so that
 * cards, charts, and metric containers are never split across pages.
 */
function applyPageBreakClasses(root: HTMLElement) {
  // Selectors for elements that must not be split across a page break
  const avoidBreakSelectors = [
    // Dashboard metric cards
    '[class*="rounded-2xl"]',
    '[class*="rounded-xl"]',
    // Chart wrappers (Recharts)
    '[class*="recharts-wrapper"]',
    '[class*="recharts-responsive-container"]',
    // AI report blocks
    ".kpi-card",
    ".kpi-grid",
    ".tracking-card",
    ".tracking-section",
    // Generic card / panel patterns
    '[class*="card"]',
    '[class*="panel"]',
    '[class*="shadow"]',
    // Table rows
    "tr",
  ].join(", ");

  try {
    root.querySelectorAll<HTMLElement>(avoidBreakSelectors).forEach((el) => {
      el.classList.add("pdf-avoid-break");
      el.style.breakInside = "avoid";
      el.style.pageBreakInside = "avoid";
    });
  } catch {
    // Silently ignore selector errors from complex class names
  }

  // Ensure table headers repeat on new pages
  root.querySelectorAll<HTMLElement>("thead").forEach((thead) => {
    thead.style.display = "table-header-group";
  });
}

/**
 * Remove or override inline-styles that restrict height or enforce hidden
 * overflow, which would otherwise clip the report when printed across pages.
 *
 * This is the critical fix for the "Strategic Recommendations cut off" bug.
 * inlineComputedStyles copies the SCREEN dimensions onto each element,
 * including fixed pixel heights that were correct for the screen viewport
 * but are too short for the narrower A4 layout where text reflows to more
 * lines.  We must force EVERY container to height:auto / overflow:visible
 * so the content can flow across as many pages as needed.
 */
function cleanupPrintStyles(root: HTMLElement) {
  // Force visible overflow and auto height on the root export container itself
  root.style.setProperty("height", "auto", "important");
  root.style.setProperty("max-height", "none", "important");
  root.style.setProperty("overflow", "visible", "important");
  root.style.setProperty("overflow-x", "visible", "important");
  root.style.setProperty("overflow-y", "visible", "important");

  // Select ALL elements in the cloned tree and remove height/overflow locks
  root.querySelectorAll<HTMLElement>("*").forEach((el) => {
    // Force overflow visible on every element — no exceptions
    el.style.setProperty("overflow", "visible", "important");
    el.style.setProperty("overflow-x", "visible", "important");
    el.style.setProperty("overflow-y", "visible", "important");

    // Force height to auto on every element — this is the key fix.
    // The inlined computed styles lock heights to their screen pixel values
    // which causes clipping when the content reflows on A4 width.
    const h = el.style.getPropertyValue("height");
    if (h && h !== "auto" && h !== "100%") {
      el.style.setProperty("height", "auto", "important");
    }

    const maxH = el.style.getPropertyValue("max-height");
    if (maxH && maxH !== "none") {
      el.style.setProperty("max-height", "none", "important");
    }

    const minH = el.style.getPropertyValue("min-height");
    if (minH && minH !== "0px" && minH !== "0" && minH !== "auto") {
      el.style.setProperty("min-height", "auto", "important");
    }
  });
}

/**
 * Centralized print/PDF CSS injected inline into the generated HTML document.
 * This mirrors the rules in styles/pdf-print.css so they are self-contained
 * and do not depend on the Next.js asset pipeline being reachable from
 * the Playwright browser context.
 */
const PDF_PRINT_CSS = `
@page {
  size: A4 portrait;
  margin: 15mm 12mm;
}

*,
*::before,
*::after {
  -webkit-print-color-adjust: exact !important;
  print-color-adjust: exact !important;
  color-adjust: exact !important;
  box-sizing: border-box;
  animation: none !important;
  transition: none !important;
}

html, body {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  height: auto !important;
  overflow: visible !important;
  widows: 2;
  orphans: 2;
}

.pdf-avoid-break,
.avoid-page-break {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

.pdf-page-break-before {
  break-before: page !important;
  page-break-before: always !important;
}

.pdf-page-break-after {
  break-after: page !important;
  page-break-after: always !important;
}

h1, h2, h3, h4, h5, h6 {
  break-after: avoid !important;
  page-break-after: avoid !important;
}

table {
  width: 100% !important;
  border-collapse: collapse !important;
}

thead {
  display: table-header-group !important;
}

tfoot {
  display: table-footer-group !important;
}

tr {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

th, td {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
  word-break: break-word;
  overflow-wrap: break-word;
}

[data-pdf-export-ignore="true"],
[data-html2canvas-ignore="true"] {
  display: none !important;
}

.pdf-export-shell {
  display: block !important;
  padding: 0 !important;
  margin: 0 !important;
}

.pdf-export-root {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}

main,
[class*="max-w"] {
  max-width: 100% !important;
}

img[data-pdf-chart] {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
  max-width: 100% !important;
  height: auto !important;
}

/* Report-specific containers */
.report__header,
.kpi-card,
.kpi-grid,
.tracking-card,
.tracking-section {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

body .report,
body .report__body {
  break-inside: auto !important;
  page-break-inside: auto !important;
  overflow: visible !important;
  height: auto !important;
  max-height: none !important;
}
`;

function buildExportHtml(element: HTMLElement) {
  const clonedRoot = element.cloneNode(true) as HTMLElement;
  const renderedWidth = Math.ceil(element.getBoundingClientRect().width);
  const bodyStyle = window.getComputedStyle(document.body);

  clonedRoot
    .querySelectorAll('[data-pdf-export-ignore="true"], [data-html2canvas-ignore="true"]')
    .forEach((node) => node.remove());

  replaceCanvasWithImages(element, clonedRoot);

  // Inline every computed style from the live DOM onto the cloned tree.
  // This is what makes the PDF look identical to the screen — without it
  // Playwright cannot resolve CSS module class names or fetch Next.js assets.
  inlineComputedStyles(element, clonedRoot);

  // Apply page-break classes AFTER styles are inlined so they override
  applyPageBreakClasses(clonedRoot);

  // Override any inlined computed height/overflow rules that cause page clipping.
  // This is the fix for "Strategic Recommendations" being cut off — the inlined
  // heights from the screen viewport are too short for the A4 reflow.
  cleanupPrintStyles(clonedRoot);

  const htmlClass = escapeHtml(document.documentElement.className);
  const bodyClass = escapeHtml(document.body.className);
  const headMarkup = collectHeadMarkup(document);
  const lang = escapeHtml(document.documentElement.lang || "en");
  const origin = escapeHtml(window.location.origin);

  return `<!DOCTYPE html>
<html lang="${lang}" class="${htmlClass}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=800, initial-scale=1" />
    <base href="${origin}" />
    ${headMarkup}
    <style>
      /* ── Inline PDF-print rules (self-contained, no network fetch needed) ── */
      ${PDF_PRINT_CSS}

      /* ── Fallback screen rules to keep the Playwright render predictable ── */
      body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        color-adjust: exact;
        background: ${bodyStyle.backgroundColor || "transparent"};
        color: ${bodyStyle.color || "inherit"};
      }

      .pdf-export-shell {
        display: flex;
        justify-content: center;
        padding: 0;
      }

      .pdf-export-root {
        width: 100%;
        max-width: ${renderedWidth}px;
      }

      [data-pdf-export-ignore="true"] {
        display: none !important;
      }
    </style>
  </head>
  <body class="${bodyClass}">
    <div class="pdf-export-shell">
      <div class="pdf-export-root">${clonedRoot.outerHTML}</div>
    </div>
  </body>
</html>`;
}

async function requestPdf(payload: PdfExportPayload) {
  const response = await fetch("/api/pdf", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "PDF export failed.";

    try {
      const data = (await response.json()) as { error?: string };
      if (data.error) {
        message = data.error;
      }
    } catch {
      const text = await response.text();
      if (text) {
        message = text;
      }
    }

    throw new Error(message);
  }

  return response.blob();
}

export async function downloadElementAsPdf(targetId: string, filename: string) {
  if (typeof window === "undefined") return;

  const element = document.getElementById(targetId);
  if (!element) {
    throw new Error("Could not find the analysis report content.");
  }

  /*
   * Temporarily remove the 'dark' theme class from <html> and <body>
   * synchronously before capturing the inline computed styles.
   * This forces the browser to evaluate styles in professional light mode
   * (which is optimal for printing/PDFs), and immediately restores dark mode
   * without any visual flicker to the user.
   */
  const htmlIsDark = document.documentElement.classList.contains("dark");
  const bodyIsDark = document.body.classList.contains("dark");

  if (htmlIsDark) document.documentElement.classList.remove("dark");
  if (bodyIsDark) document.body.classList.remove("dark");

  // Force a synchronous style recalc so getComputedStyle returns light-mode values
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  element.offsetHeight;

  let htmlContent: string;
  try {
    htmlContent = buildExportHtml(element);
  } finally {
    if (htmlIsDark) document.documentElement.classList.add("dark");
    if (bodyIsDark) document.body.classList.add("dark");
  }

  /*
   * Viewport width passed to the server is now 800 px — the A4-equivalent
   * width that matches the Playwright viewport set in route.ts.
   * This ensures the inlined computed styles are calculated at 800 px so
   * they match what Playwright renders, preventing any width mismatch.
   */
  const pdfBlob = await requestPdf({
    filename: filename || "analysis-report.pdf",
    html: htmlContent,
    viewportWidth: 800,
  });

  const url = window.URL.createObjectURL(pdfBlob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "analysis-report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
