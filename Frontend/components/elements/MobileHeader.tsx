"use client"

import { Button } from "@/components/ui/button"
import { ChevronLeft, Menu } from "lucide-react"
import { useSidebar } from "@/components/ui/sidebar"
import { usePathname, useRouter } from "next/navigation"
import { useLanguage } from "@/providers/language-provider"

export default function MobileHeader() {
  const { setOpen } = useSidebar()
  const router = useRouter()
  const pathname = usePathname()
  const { t } = useLanguage()

  return (
    <div className="lg:hidden flex items-center justify-between gap-3 p-4 bg-gray-100 dark:bg-[#1E2939] border-b border-gray-200 dark:border-gray-800">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(true)}
        className="mr-2"
      >
        <Menu className="h-6 w-6" />
      </Button>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-sm font-bold">H</span>
        </div>
        <div>
          <div className="font-semibold text-sm">{t("hospitalityAi")}</div>
          <div className="text-xs text-green-500">{t("aiAssistantActive")}</div>
        </div>
      </div>

      {pathname !== "/dashboard" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/dashboard")}
          className="ml-auto"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          {t("dashboard")}
        </Button>
      )}
    </div>
  )
}