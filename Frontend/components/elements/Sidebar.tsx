"use client"

import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  ChevronLeft,
  Plus,
  BarChart3,
  Users,
  Wine,
  ChefHat,
  Lightbulb,
  TrendingUp,
  FileSpreadsheet,
  User,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useSidebar } from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useLanguage } from "@/providers/language-provider"
import type { Language } from "@/lib/translations"

const chatHistory = [
  { id: 1, titleKey: "kpiAnalysis" as const, titleSuffix: " - Labor Cost Analysis", href: "/dashboard/kpi-analysis" },
  { id: 2, titleKey: "hrOptimization" as const, titleSuffix: " Review", href: "/dashboard/hr-optimization" },
  { id: 3, titleKey: "beverageInsights" as const, titleSuffix: " Check", href: "/dashboard/beverage-insights" },
  { id: 4, titleKey: "menuEngineering" as const, titleSuffix: " Review", href: "/dashboard/menu-engineering" },
  { id: 5, titleKey: "recipeIntelligence" as const, titleSuffix: " Analysis", href: "/dashboard/recipe-intelligence" },
  { id: 6, titleKey: "strategicPlanning" as const, titleSuffix: " Session", href: "/dashboard/strategic-planning" },
  { id: 7, titleKey: "csvKpiDashboard" as const, titleSuffix: " Review", href: "/dashboard/csv-kpi-dashboard" },
]

const features = [
  { icon: BarChart3, labelKey: "kpiAnalysis" as const, href: "/dashboard/kpi-analysis" },
  { icon: Users, labelKey: "hrOptimization" as const, href: "/dashboard/hr-optimization" },
  { icon: Wine, labelKey: "beverageInsights" as const, href: "/dashboard/beverage-insights" },
  { icon: ChefHat, labelKey: "menuEngineering" as const, href: "/dashboard/menu-engineering" },
  { icon: Lightbulb, labelKey: "recipeIntelligence" as const, href: "/dashboard/recipe-intelligence" },
  { icon: TrendingUp, labelKey: "strategicPlanning" as const, href: "/dashboard/strategic-planning" },
  { icon: FileSpreadsheet, labelKey: "csvKpiDashboard" as const, href: "/dashboard/csv-kpi-dashboard" },
]

export default function Sidebar() {
  const { open, setOpen } = useSidebar()
  const router = useRouter()
  const pathname = usePathname()
  const { language, setLanguage, t } = useLanguage()
  const selectedFeature = features.find(feature => feature.href === pathname)?.labelKey || "kpiAnalysis"

  const handleFeatureClick = (feature: typeof features[0]) => {
    router.push(feature.href)
    // Close sidebar on mobile after click
    if (window.innerWidth < 1024) {
      setOpen(false)
    }
  }

  const handleChatHistoryClick = (chat: typeof chatHistory[0]) => {
    router.push(chat.href)
    // Close sidebar on mobile after click
    if (window.innerWidth < 1024) {
      setOpen(false)
    }
  }

  return (
    <>
      {/* Mobile Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 w-64 flex flex-col bg-gray-100 dark:bg-[#1E2939] border-r border-gray-200 dark:border-gray-800 transition-transform duration-300 ease-in-out",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">H</span>
            </div>
            <div>
              <div className="font-semibold text-sm text-gray-900 dark:text-white">{t("hospitalityAi")}</div>
              <div className="text-xs text-green-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                {t("aiAssistantActive")}
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setOpen(false)}
            className="lg:hidden"
          >
            <ChevronLeft className="h-5 w-5" />
          </Button>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <Button
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium"
            onClick={() => {
              router.push("/dashboard")
              if (window.innerWidth < 1024) setOpen(false)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("newChat")}
          </Button>
        </div>

        {/* Chat History */}
        <div className="px-4 mb-4">
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            {t("chatHistory")}
          </h3>
          <ScrollArea className="h-48">
            <div className="space-y-1">
              {chatHistory.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => handleChatHistoryClick(chat)}
                  className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors truncate"
                >
                  {t(chat.titleKey)}{chat.titleSuffix}
                </button>
              ))}
            </div>
          </ScrollArea>
          <Button variant="outline" className="w-full mt-2" onClick={() => router.push("/dashboard/history")}>
            {t("seeAllHistory")}
          </Button>
        </div>

        {/* Features */}
        <div className="flex-1 px-4 overflow-hidden">
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            {t("features")}
          </h3>
          <ScrollArea className="h-full pb-4">
            <div className="space-y-1">
              {features.map((feature) => {
                const Icon = feature.icon
                const label = t(feature.labelKey)
                const isSelected = selectedFeature === feature.labelKey

                return (
                  <button
                    key={feature.labelKey}
                    onClick={() => handleFeatureClick(feature)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group",
                      isSelected
                        ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white"
                    )}
                  >
                    <Icon className={cn("h-4 w-4", isSelected ? "text-white" : "text-gray-500 group-hover:text-current")} />
                    <span>{label}</span>
                    {isSelected && (
                      <div className="ml-auto w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                    )}
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800 space-y-1">
          <button
            onClick={() => router.push("/dashboard/profile")}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
          >
            <User className="h-4 w-4" />
            {t("userProfile")}
          </button>
          <Select
            value={language}
            onValueChange={(value) => {
              setLanguage(value as Language)
            }}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder={t("selectLanguage")} />
            </SelectTrigger>

            <SelectContent align="end">
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="es">Spanish</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </aside>
    </>
  )
}