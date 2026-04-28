"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useLanguage } from "@/providers/language-provider";
import { downloadElementAsPdf } from "@/services/pdfService";

interface DownloadPdfButtonProps {
  targetId: string;
  filename: string;
}

export function DownloadPdfButton({ targetId, filename }: DownloadPdfButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { t } = useLanguage();

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      await downloadElementAsPdf(targetId, filename);
    } catch (error) {
      console.error("PDF Export Error:", error);
      alert(`Export failed: ${error instanceof Error ? error.message : "Check console"}`);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Button
      id={`pdf-btn-${targetId}`}
      data-pdf-export-ignore="true"
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
