"use client"

import { useState, useRef, useEffect } from "react"
import DOMPurify from "dompurify"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  TrendingUp,
  CheckCircle2,
  Send,
  Paperclip,
  User,
  Bot,
  Utensils,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Textarea } from "@/components/ui/textarea"
import { sendChatMessage, uploadCsv } from "@/services/menuService"
import styles from "./menuReportStyles.module.css"

import { useLanguage } from "@/providers/language-provider"
import { DownloadPdfButton } from "@/components/dashboard/DownloadPdfButton"

// analysisCards moved inside the component to use t()

type ChatMessage = {
  id: number
  type: "user" | "ai"
  text?: string
  html?: string
}

function sanitizeMenuHtml(dirtyHtml: string): string {
  if (typeof window === "undefined") return ""
  return DOMPurify.sanitize(dirtyHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ["style", "class"],
    FORCE_BODY: true,
  })
}

export default function MenuEngineering() {
  const { language, t } = useLanguage()
  const [selectedCard, setSelectedCard] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analysisCards = [
    {
      id: "analysis",
      icon: TrendingUp,
      title: t("menuAnalysisTitle"),
      iconBg: "bg-green-500",
      features: [t("salesMixAnalysis"), t("contributionMargins"), t("menuMatrixMapping")],
      samplePrompt: t("menuAnalysisSample"),
    },
    {
      id: "pricing",
      icon: TrendingUp,
      title: t("pricingStrategyTitle"),
      iconBg: "bg-purple-500",
      features: [t("priceElasticity"), t("competitiveAnalysis"), t("profitMaximization")],
      samplePrompt: t("menuPricingSample"),
    },
    {
      id: "optimization",
      icon: Utensils,
      title: t("itemOptimizationTitle"),
      iconBg: "bg-cyan-500",
      features: [t("recipeCosting"), t("portionControl"), t("descriptionOptimization")],
      samplePrompt: t("menuOptimizationSample"),
    },
  ]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleCardClick = (cardId: string) => {
    const card = analysisCards.find((c) => c.id === cardId)
    if (!card) return
    setSelectedCard(cardId)
    setInputValue(card.samplePrompt)
    setError(null)
  }

  const handleSendMessage = async () => {
    const trimmed = inputValue.trim()
    if (!trimmed || isLoading) return

    const userMsg: ChatMessage = { id: Date.now(), type: "user", text: trimmed }
    setMessages((prev) => [...prev, userMsg])
    setInputValue("")
    setIsLoading(true)
    setError(null)

    try {
      const response = await sendChatMessage(trimmed, language)
      const aiMsg: ChatMessage = {
        id: Date.now() + 1,
        type: "ai",
        html: sanitizeMenuHtml(response.html_response),
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleCsvUpload = async (file: File) => {
    if (!file) return
    setIsLoading(true)
    setError(null)

    const userMsg: ChatMessage = {
      id: Date.now(),
      type: "user",
      text: `${t("uploadedCsv")} ${file.name}`,
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const formData = new FormData()
      formData.append("required_csv", file)
      if (selectedCard) formData.append("analysis_type", selectedCard)

      const response = await uploadCsv(formData, language)
      const aiMsg: ChatMessage = {
        id: Date.now() + 1,
        type: "ai",
        html: sanitizeMenuHtml(response.html_response),
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      setError(err instanceof Error ? err.message : t("csvError"))
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-black">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleCsvUpload(file)
          e.target.value = ""
        }}
      />

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-4 py-8">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="bg-gradient-to-r from-[#C27AFF] via-[#51A2FF] to-[#C27AFF] bg-clip-text text-transparent text-4xl font-semibold text-center mb-4">
              {t("menuEngineering")}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-lg whitespace-pre-line">
              {t("menuEngineeringSubtitle")}
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
              <strong>{t("error")}:</strong> {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {analysisCards.map((card) => {
              const Icon = card.icon
              const isSelected = selectedCard === card.id
              return (
                <Card
                  key={card.id}
                  onClick={() => handleCardClick(card.id)}
                  className={cn(
                    "p-6 cursor-pointer transition-all duration-300 border-2",
                    isSelected
                      ? "bg-gradient-to-br from-[#052B7D] to-[#000A4E] border-blue-500"
                      : "bg-gray-100 dark:bg-[#1E2939] border-transparent hover:border-gray-600"
                  )}
                >
                  <div className="flex flex-col items-center text-center">
                    <div
                      className={cn(
                        "w-12 h-12 rounded-lg flex items-center justify-center mb-4",
                        card.iconBg
                      )}
                    >
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <h3
                      className={cn(
                        "text-lg font-semibold mb-4",
                        isSelected ? "text-white" : "text-gray-900 dark:text-white"
                      )}
                    >
                      {card.title}
                    </h3>
                    <ul className="space-y-2 text-sm">
                      {card.features.map((feature, idx) => (
                        <li
                          key={idx}
                          className={cn(
                            "flex items-start gap-2",
                            isSelected ? "text-gray-300" : "text-gray-600 dark:text-gray-400"
                          )}
                        >
                          <CheckCircle2
                            className={cn(
                              "size-5 mt-0.5 flex-shrink-0",
                              isSelected ? "text-cyan-400" : "text-cyan-500"
                            )}
                          />
                          <span className="mt-0.5">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </Card>
              )
            })}
          </div>

          <div className="space-y-4 pb-4 lg:min-h-[88px] xl:min-h-80">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3",
                  message.type === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.type === "ai" && (
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-3xl rounded-2xl",
                    message.type === "user"
                      ? "px-6 py-4 bg-gradient-to-br from-[#9810FA] to-[#155DFC] text-white"
                      : message.html &&
                          (message.html.includes('class=\"report') ||
                            message.html.includes("class='report"))
                        ? "p-0 bg-transparent"
                        : "px-6 py-4 bg-gray-100 dark:bg-[#1E2939] text-gray-900 dark:text-white"
                  )}
                >
                  {message.html ? (
                    <div id={`report-${message.id}`} className="relative w-full">
                      {(message.html.includes("class=\"report") || message.html.includes("class='report") || message.html.includes("report__header")) && (
                        <DownloadPdfButton targetId={`report-${message.id}`} filename="menu_engineering.pdf" />
                      )}
                      <div
                        className={cn(
                          styles.menuHtml,
                          "prose prose-sm max-w-none whitespace-normal dark:prose-invert"
                        )}
                        dangerouslySetInnerHTML={{ __html: sanitizeMenuHtml(message.html) }}
                      />
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{message.text}</p>
                  )}
                </div>
                {message.type === "user" && (
                  <div className="w-10 h-10 rounded-lg bg-gray-600 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-white" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="max-w-3xl rounded-2xl px-6 py-4 bg-gray-100 dark:bg-[#1E2939]">
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-black">
        <div className="max-w-5xl mx-auto p-4">
          <div className="flex gap-2 items-center bg-gray-100 dark:bg-[#1E2939] rounded-xl px-4 py-3 border border-gray-300 dark:border-gray-700">
            <Button
              variant="ghost"
              size="icon"
              disabled={isLoading}
              onClick={() => fileInputRef.current?.click()}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={isLoading}
              placeholder={t("menuInputPlaceholder")}
              className="flex-1 resize-none overflow-hidden min-h-5 max-h-32 bg-transparent border-none text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-500 focus-visible:ring-0 focus-visible:ring-offset-0"
              rows={1}
            />
            <Button
              onClick={handleSendMessage}
              size="icon"
              disabled={isLoading || !inputValue.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-center text-xs text-gray-500 mt-2">
            {t("menuFooterHint")}
          </p>
        </div>
      </div>
    </div>
  )
}
