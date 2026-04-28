"use client";

interface PdfExportPayload {
  filename: string;
  html: string;
  viewportWidth: number;
}

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
      image.style.display = "block";
      image.style.width = `${sourceCanvas.clientWidth || sourceCanvas.width}px`;
      image.style.maxWidth = "100%";
      image.style.height = "auto";
      clonedCanvas.replaceWith(image);
    } catch {
      // If a canvas cannot be serialized, keep the original node in place.
    }
  });
}

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

function buildExportHtml(element: HTMLElement) {
  const clonedRoot = element.cloneNode(true) as HTMLElement;
  const renderedWidth = Math.ceil(element.getBoundingClientRect().width);
  const renderedHeight = Math.ceil(element.getBoundingClientRect().height);
  const bodyStyle = window.getComputedStyle(document.body);

  clonedRoot
    .querySelectorAll('[data-pdf-export-ignore="true"], [data-html2canvas-ignore="true"]')
    .forEach((node) => node.remove());

  replaceCanvasWithImages(element, clonedRoot);
  inlineComputedStyles(element, clonedRoot);

  const htmlClass = escapeHtml(document.documentElement.className);
  const bodyClass = escapeHtml(document.body.className);
  const headMarkup = collectHeadMarkup(document);
  const lang = escapeHtml(document.documentElement.lang || "en");
  const origin = escapeHtml(window.location.origin);

  return `<!DOCTYPE html>
<html lang="${lang}" class="${htmlClass}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <base href="${origin}" />
    ${headMarkup}
    <style>
      @page {
        size: A4;
        margin: 0;
      }

      html,
      body {
        margin: 0;
        padding: 0;
      }

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
        min-height: ${renderedHeight}px;
      }

      [data-pdf-export-ignore="true"] {
        display: none !important;
      }

      * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color-adjust: exact !important;
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

  const pdfBlob = await requestPdf({
    filename: filename || "analysis-report.pdf",
    html: buildExportHtml(element),
    viewportWidth: Math.max(window.innerWidth, 1280),
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
