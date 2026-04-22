"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useLanguage } from "@/providers/language-provider";

interface DownloadPdfButtonProps {
  targetId: string;
  filename: string;
}

export function DownloadPdfButton({ targetId, filename }: DownloadPdfButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { t } = useLanguage();

  const handleDownload = async () => {
    if (typeof window === "undefined") return;
    
    try {
      setIsDownloading(true);
      const element = document.getElementById(targetId);
      if (!element) {
        alert("Could not find the analysis report content.");
        setIsDownloading(false);
        return;
      }

      // Import the library safely
      const html2pdfModule = await import("html2pdf.js");
      const html2pdf = html2pdfModule.default || html2pdfModule;

      if (typeof html2pdf !== 'function') {
        throw new Error("PDF library not loaded correctly");
      }

      // Define options
      const opt = {
        margin: [15, 10, 15, 10], // Slightly more margin
        filename: filename || 'analysis-report.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
          scale: 2, 
          useCORS: true, 
          letterRendering: true,
          backgroundColor: '#ffffff',
          onclone: (clonedDoc: Document) => {
            const container = clonedDoc.getElementById(targetId);
            clonedDoc.body.classList.remove('dark');
            if (container) {
                container.classList.remove('dark');
                container.style.backgroundColor = '#ffffff';
                container.style.color = '#333333';
                
                // Scrub modern colors
                const all = container.getElementsByTagName("*");
                for (let i = 0; i < all.length; i++) {
                  const el = all[i] as HTMLElement;
                  const s = window.getComputedStyle(el);
                  if (s.backgroundColor.match(/oklch|lab/)) el.style.backgroundColor = '#ffffff';
                  if (s.color.match(/oklch|lab/)) el.style.color = '#333333';
                  if (el.className.includes('report__header')) {
                      el.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                      el.style.color = '#ffffff';
                  }
                }
            }
          }
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };

      // Generate PDF
      await html2pdf().from(element).set(opt).save();
      setIsDownloading(false);

    } catch (e: any) {
      console.error("PDF Export Error:", e);
      alert(`Export failed: ${e.message || 'Check console'}`);
      setIsDownloading(false);
    }
  };

  return (
    <Button
      id={`pdf-btn-${targetId}`}
      data-html2canvas-ignore="true"
      variant="outline"
      size="sm"
      className="absolute top-4 right-4 z-[999] bg-white/90 hover:bg-white text-[#052B7D] dark:bg-[#1E2939]/90 dark:hover:bg-[#1E2939] dark:text-white border border-gray-200 dark:border-gray-700 shadow-md transition-all duration-200 backdrop-blur-sm"
      onClick={handleDownload}
      disabled={isDownloading}
    >
      <Download className="w-4 h-4 mr-2" />
      {isDownloading ? t("downloading") : t("downloadPdf")}
    </Button>
  );
}
