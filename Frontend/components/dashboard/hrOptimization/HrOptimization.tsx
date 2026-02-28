"use client"

import { useState, useRef, useEffect } from "react"
import DOMPurify from "dompurify"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Users,
  TrendingUp,
  CheckCircle2,
  Send,
  Paperclip,
  User,
  BotIcon,
  ClipboardCheck,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Textarea } from "@/components/ui/textarea"
import { sendChatMessage, uploadCsv } from "@/services/hrService"
import styles from "./hrReportStyles.module.css"

const analysisCards = [
  {
    id: "retention",
    icon: Users,
    title: "Staff Retention",
    iconBg: "bg-green-500",
    samplePrompt:
      "Staff retention sample: turnover_rate: 0.45, industry_average: 0.70, department: Front of House, employee_count: 25",
    features: [
      "Turnover analysis ",
      "Retention strategies",
      "Cost impact assessment",
    ],
  },
  {
    id: "scheduling",
    icon: ClipboardCheck,
    title: "Labor Scheduling",
    iconBg: "bg-purple-500",
    samplePrompt:
      "Labor scheduling sample: total_sales: 50000, labor_hours: 800, hourly_rate: 15, peak_hours: 200, date: 2026-02-01, department: Kitchen.",
    features: [
      "Shift optimization",
      "Peak hour coverage",
      "Overtime management",
    ],
  },
  {
    id: "performance",
    icon: TrendingUp,
    title: "Training Programs",
    iconBg: "bg-cyan-500",
    samplePrompt:
      "Training programs sample: customer_satisfaction: 0.85, sales_performance: 0.95, efficiency_score: 0.80, attendance_rate: 0.92, employee name: Alex Rivera, department: Service",
    features: [
      "Onboarding optimization",
      "Skill development",
      "Performance tracking",
    ],
  },
]

type ChatMessage = {
  id: number
  type: "user" | "ai"
  text?: string
  html?: string
}

function sanitizeHrHtml(dirtyHtml: string): string {
  return DOMPurify.sanitize(dirtyHtml, {
    USE_PROFILES: { html: true },
    ADD_TAGS: ["style"],
    ADD_ATTR: ["class", "style", "id"],
    FORBID_TAGS: ["script", "iframe", "object", "embed"],
    KEEP_CONTENT: true,
  })
}

export default function HROptimization() {
  const [selectedCard, setSelectedCard] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    const message = inputValue.trim()
    if (!message || isLoading) return

    setError(null)
    setIsLoading(true)

    const baseId = Date.now()

    setMessages((prev) => [...prev, { id: baseId, type: "user", text: message }])
    setInputValue("")

    try {
      const { html_response } = await sendChatMessage(message)
      setMessages((prev) => [...prev, { id: baseId + 1, type: "ai", html: html_response }])
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong."
      setError(msg)
      setMessages((prev) => [...prev, { id: baseId + 1, type: "ai", text: `Error: ${msg}` }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleCardClick = (cardId: string) => {
    setSelectedCard(cardId)
    const card = analysisCards.find((c) => c.id === cardId)
    if (card?.samplePrompt) setInputValue(card.samplePrompt)
  }

  const handlePickCsv = () => {
    if (isLoading) return
    fileInputRef.current?.click()
  }

  const handleCsvSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ""

    if (!files.length || isLoading) return

    setError(null)
    setIsLoading(true)

    const baseId = Date.now()

    setMessages((prev) => [
      ...prev,
      {
        id: baseId,
        type: "user",
        text:
          files.length === 1
            ? `Uploaded CSV: ${files[0].name}`
            : `Uploaded CSVs: ${files.map((f) => f.name).join(", ")}`,
      },
    ])

    try {
      const formData = new FormData()
      formData.append("required_csv", files[0])
      if (files[1]) formData.append("optional_csv", files[1])

      const { html_response } = await uploadCsv(formData)
      setMessages((prev) => [...prev, { id: baseId + 1, type: "ai", html: html_response }])
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong."
      setError(msg)
      setMessages((prev) => [...prev, { id: baseId + 1, type: "ai", text: `Error: ${msg}` }])
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
      {/* Chat Messages Area - Scrollable */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-8"
      >
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="bg-gradient-to-r from-[#C27AFF] via-[#51A2FF] to-[#C27AFF] bg-clip-text text-transparent text-4xl font-semibold text-center mb-4">
              HR Optimization
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-lg">
              Optimize your workforce management with AI-driven insights
              <br />
              for retention, scheduling, and performance tracking.
            </p>
          </div>

          {/* Analysis Cards */}
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
                        isSelected
                          ? "text-white"
                          : "text-gray-900 dark:text-white"
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
                            isSelected
                              ? "text-gray-300"
                              : "text-gray-600 dark:text-gray-400"
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

          {/* Chat Messages */}
          <div className="space-y-4 pb-4 lg:min-h-[88px] xl:min-h-80">
            {error && <div className="text-sm text-red-500 px-2">{error}</div>}
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
                    <BotIcon stroke="white" />
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-3xl rounded-2xl",
                    message.type === "user"
                      ? "px-6 py-4 bg-gradient-to-br from-[#9810FA] to-[#155DFC] text-white"
                      : message.html &&
                          (message.html.includes('class="report"') ||
                            message.html.includes("class='report'"))
                        ? "p-0 bg-transparent"
                        : "px-6 py-4 bg-gray-100 dark:bg-[#1E2939] text-gray-900 dark:text-white"
                  )}
                >
                  {message.type === "ai" && message.html ? (
                    <div
                      className={cn(
                        styles.hrHtml,
                        "prose prose-sm max-w-none whitespace-normal dark:prose-invert"
                      )}
                      dangerouslySetInnerHTML={{
                        __html: sanitizeHrHtml(message.html),
                      }}
                    />
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

            {/* Animated loading dots (match KPI Analysis page) */}
            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0">
                  <BotIcon stroke="white" className="w-5 h-5" />
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
            {/* Invisible div to scroll to */}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Input Area - Fixed at Bottom */}
      <div className="sticky bottom-0 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-black">
        <div className="max-w-5xl mx-auto p-4">
          <div className="flex gap-2 items-center bg-gray-100 dark:bg-[#1E2939] rounded-xl px-4 py-3 border border-gray-300 dark:border-gray-700">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              multiple
              onChange={handleCsvSelected}
              className="hidden"
            />
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              onClick={handlePickCsv}
              disabled={isLoading}
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Enter HR inputs as key:value pairs (e.g., turnover_rate: 45, industry_average: 70)"
              disabled={isLoading}
              className="flex-1 resize-none overflow-hidden min-h-5 max-h-32 bg-transparent border-none text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-500 focus-visible:ring-0 focus-visible:ring-offset-0"
              rows={1}
            />
            <Button
              onClick={handleSendMessage}
              size="icon"
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              disabled={isLoading}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-center text-xs text-gray-500 mt-2">
            Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}