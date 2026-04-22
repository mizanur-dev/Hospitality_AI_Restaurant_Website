"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import DOMPurify from "dompurify";
import {
  sendChatMessage as sendKpiChatMessage,
  uploadCsv as uploadKpiCsv,
} from "@/services/kpiService";
import {
  sendChatMessage as sendHrChatMessage,
  uploadCsv as uploadHrCsv,
} from "@/services/hrService";
import {
  sendChatMessage as sendBeverageChatMessage,
  uploadCsv as uploadBeverageCsv,
} from "@/services/beverageService";
import {
  sendChatMessage as sendMenuChatMessage,
  uploadCsv as uploadMenuCsv,
} from "@/services/menuService";
import {
  sendChatMessage as sendRecipeChatMessage,
  uploadCsv as uploadRecipeCsv,
} from "@/services/recipeService";
import {
  sendChatMessage as sendStrategicChatMessage,
  uploadCsv as uploadStrategicCsv,
} from "@/services/strategicService";
import styles from "@/components/dashboard/kpiAnalysis/kpiReportStyles.module.css";
import { DownloadPdfButton } from "@/components/dashboard/DownloadPdfButton";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  BarChart3,
  Users,
  Wine,
  ChefHat,
  Lightbulb,
  TrendingUp,
  Send,
  Paperclip,
  User,
  BotIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/providers/language-provider";
import type { TranslationKey } from "@/lib/translations";

// mainCards moved inside the component to use t()
const CHAT_API_URL =
  process.env.NEXT_PUBLIC_CHAT_API_URL ??
  `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}/chat/api/`;

type Domain = "kpi" | "hr" | "beverage" | "menu" | "recipe" | "strategic" | "general";

function normalizeText(s: string): string {
  return (s || "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
}

function looksLikeGreeting(message: string): boolean {
  const n = normalizeText(message);
  return (
    n === "hi" ||
    n === "hello" ||
    n === "hey" ||
    n === "good morning" ||
    n === "good afternoon" ||
    n === "good evening" ||
    n.startsWith("hi ") ||
    n.startsWith("hello ") ||
    n.startsWith("hey ")
  );
}

function detectDomainFromText(message: string): Domain {
  const n = normalizeText(message);
  if (!n) return "general";

  // Prefer "general" for greetings / generic conversation.
  if (looksLikeGreeting(n)) return "general";

  // Strategic
  if (/(\bswot\b|strengths?|weakness(es)?|opportunit(y|ies)|threats?)/i.test(message)) return "strategic";
  if (/(business goals?|growth strategy|market size|market share|investment budget|revenue target|budget total)/i.test(message)) return "strategic";

  // Recipe
  if (/(\brecipe\b|ingredients?|servings?|prep time|cook time|portion cost|yield percentage|scale (my )?recipe)/i.test(message)) return "recipe";

  // Beverage
  if (/(liquor|bar inventory|beverage pricing|expected oz|actual oz|drink price|cost per drink|inventory value|reorder point)/i.test(message)) return "beverage";

  // HR
  if (/(turnover|retention|onboarding|training program|performance management|labor scheduling|shift optimization|attendance)/i.test(message)) return "hr";

  // Menu
  if (/(menu analysis|menu engineering|contribution margin|sales mix|competitor price|item optimization|waste percent|portion size)/i.test(message)) return "menu";

  // KPI / Cost
  if (/(kpi|prime cost|food cost|labor cost|sales per hour|revpash|covers served|total sales)/i.test(message)) return "kpi";

  return "general";
}

function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  out.push(cur.trim());
  return out.filter(Boolean);
}

async function readCsvHeaders(file: File): Promise<Set<string>> {
  const text = await file.slice(0, 64 * 1024).text();
  const firstLine = text.split(/\r?\n/).find((l) => l.trim().length > 0) || "";
  const cols = parseCsvLine(firstLine)
    .map((c) => c.toLowerCase().trim())
    .filter(Boolean);
  // Normalize columns to allow fuzzy matching (spaces/underscores/hyphens ignored)
  const normalized = cols.map((c) => c.replace(/[\s_-]+/g, ""));
  return new Set(normalized);
}

function detectDomainFromCsvHeaders(headers: Set<string>): Domain {
  const has = (k: string) => headers.has(k.replace(/[\s_-]+/g, "").toLowerCase());

  // Beverage
  if (has("expected_oz") || has("actual_oz") || has("liquor_cost") || has("drink_price") || has("cost_per_drink")) return "beverage";
  if (has("current_stock") || has("reorder_point") || has("monthly_usage") || has("inventory_value")) return "beverage";

  // Recipe — must come before menu because recipe CSVs share "portion_cost" / "servings"
  // with menu schemas. Prioritise unambiguous recipe-specific columns first.
  if (has("recipe_name") || has("recipe_price") || has("ingredient_cost")) return "recipe";
  if (has("ingredients") || has("ingredient") || has("prep_time") || has("cook_time")) return "recipe";
  if (has("servings") && (has("portion_cost") || has("labor_cost")) && !has("sales")) return "recipe";

  // Menu
  if (has("competitor_price") || has("contribution_margin") || has("sales_mix") || has("menu_item") || has("item_name")) return "menu";
  if (has("quantity_sold") || has("waste_percent") || has("portion_cost") || has("portion_size")) return "menu";

  // KPI — must come before HR because KPI CSVs contain labor_hours/overtime_hours too.
  // Unambiguous KPI-only signals first.
  if (has("avg_check") || has("covers") || has("revpash") || has("prime_cost")) return "kpi";
  if (has("beginning_inventory") || has("ending_inventory") || has("previous_sales")) return "kpi";
  if (has("food_cost") && has("sales")) return "kpi";
  if (has("sales") && has("labor_cost")) return "kpi";
  if (has("food_cost") || has("prime_cost") || has("hours_worked")) return "kpi";

  // HR — only after KPI so labor_hours+overtime_hours in KPI CSVs don't trigger HR.
  if (has("turnover_rate") || has("retention_rate") || has("employee_name") || has("attendance_rate") || has("shift")) return "hr";
  if (has("labor_hours") && (has("hourly_rate") || has("overtime_hours"))) return "hr";

  // Strategic — business_goals, growth_strategy, sales_forecasting, operational_excellence
  if (has("revenue_target") || has("budget_total") || has("marketing_spend")) return "strategic";
  if (has("market_size") || has("market_share") || has("competition_level") || has("investment_budget")) return "strategic";
  if (has("growth_potential") || has("market_penetration") || has("target_roi")) return "strategic";
  if (has("historical_sales") || has("seasonal_factor") || has("forecast_period") || has("trend_strength")) return "strategic";
  if (has("market_growth") || has("confidence_level") || has("growth_rate")) return "strategic";
  if (has("efficiency_score") || has("process_time") || has("quality_rating") || has("customer_satisfaction")) return "strategic";
  if (has("cost_per_unit") || has("productivity_score") || has("industry_benchmark")) return "strategic";

  return "kpi"; // default to KPI endpoint (it returns helpful column mismatch messages)
}

interface Message {
  id: number;
  type: "user" | "ai";
  text: string;
}

export default function NewChat() {
  const router = useRouter();
  const { language, t } = useLanguage();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const mainCards = [
    { id: "kpi", titleKey: "kpiAnalysis" as TranslationKey, icon: BarChart3, iconBg: "bg-purple-600", route: "/dashboard/kpi-analysis" },
    { id: "hr", titleKey: "hrOptimizations" as TranslationKey, icon: Users, iconBg: "bg-green-600", route: "/dashboard/hr-optimization" },
    { id: "beverage", titleKey: "beverageInsights" as TranslationKey, icon: Wine, iconBg: "bg-red-600", route: "/dashboard/beverage-insights" },
    { id: "menu", titleKey: "menuEngineering" as TranslationKey, icon: ChefHat, iconBg: "bg-pink-600", route: "/dashboard/menu-engineering" },
    { id: "recipe", titleKey: "recipeIntelligence" as TranslationKey, icon: Lightbulb, iconBg: "bg-blue-600", route: "/dashboard/recipe-intelligence" },
    { id: "strategic", titleKey: "strategicPlanning" as TranslationKey, icon: TrendingUp, iconBg: "bg-cyan-600", route: "/dashboard/strategic-planning" },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleCardClick = (route: string) => {
    router.push(route);
  };

  const handleCsvUpload = useCallback(
    async (files: File[]) => {
      if (!files.length || isLoading) return;

      const userMessage: Message = {
        id: Date.now(),
        type: "user",
        text:
          files.length === 1
            ? `${t("uploadedCsv")} ${files[0].name}`
            : `${t("uploadedCsvs")} ${files.map((f) => f.name).join(", ")}`,
      };
      setMessages((prev) => [...prev, userMessage]);

      setIsLoading(true);
      try {
        const headers = await readCsvHeaders(files[0]);
        const domain = detectDomainFromCsvHeaders(headers);

        const formData = new FormData();
        formData.append("required_csv", files[0]);
        if (files[1]) formData.append("optional_csv", files[1]);
        // Optional hint used by some endpoints; safe to include everywhere.
        formData.append("analysis_type", "auto");

        let html_response: string;
        if (domain === "hr") {
          ({ html_response } = await uploadHrCsv(formData, language));
        } else if (domain === "beverage") {
          ({ html_response } = await uploadBeverageCsv(formData, language));
        } else if (domain === "menu") {
          ({ html_response } = await uploadMenuCsv(formData, language));
        } else if (domain === "recipe") {
          ({ html_response } = await uploadRecipeCsv(formData, language));
        } else if (domain === "strategic") {
          ({ html_response } = await uploadStrategicCsv(formData, language));
        } else {
          ({ html_response } = await uploadKpiCsv(formData, language));
        }

        setMessages((prev) => [...prev, { id: Date.now(), type: "ai", text: html_response }]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            type: "ai",
            text: `${t("csvError")} ${(err as Error).message}`,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, language, t]
  );

  const sendChat = useCallback(
    async (text: string) => {
      setIsLoading(true);
      try {
        const domain = detectDomainFromText(text);

        // General conversational chat (handles greetings and open-ended Q&A)
        if (domain === "general") {
          const res = await fetch(CHAT_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, context: null, language }),
          });
          if (!res.ok) throw new Error(`Server error: ${res.status}`);
          const data = await res.json();
          const responseText = (data?.response as string) ?? "Sorry, I could not generate a response.";
          setMessages((prev) => [...prev, { id: Date.now(), type: "ai", text: responseText }]);
          return;
        }

        // Domain chat routes to the same analysis engines as the dedicated pages.
        let html_response: string;
        if (domain === "kpi") {
          ({ html_response } = await sendKpiChatMessage(text, language));
        } else if (domain === "hr") {
          ({ html_response } = await sendHrChatMessage(text, language));
        } else if (domain === "beverage") {
          ({ html_response } = await sendBeverageChatMessage(text, language));
        } else if (domain === "menu") {
          ({ html_response } = await sendMenuChatMessage(text, language));
        } else if (domain === "recipe") {
          ({ html_response } = await sendRecipeChatMessage(text, language));
        } else {
          ({ html_response } = await sendStrategicChatMessage(text, language));
        }
        setMessages((prev) => [...prev, { id: Date.now(), type: "ai", text: html_response }]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            type: "ai",
            text: t("serverError"),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [language]
  );

  const handleSendMessage = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading) return;
    const userMessage: Message = {
      id: Date.now(),
      type: "user",
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    sendChat(trimmed);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-black">
      {/* Chat Messages Area - Scrollable */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-8"
      >
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8 sm:mb-12">
            <h1 className="bg-gradient-to-r from-[#C27AFF] via-[#51A2FF] to-[#C27AFF] bg-clip-text text-transparent text-3xl sm:text-4xl lg:text-5xl font-semibold mb-3 sm:mb-4">
              {t("yourHospitalityAiAssistant")}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base lg:text-lg px-4 whitespace-pre-line">
              {t("newChatSubtitle")}
            </p>
          </div>

          {/* Main Feature Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8">
            {mainCards.map((card) => {
              const Icon = card.icon;
              return (
                <Card
                  key={card.id}
                  onClick={() => handleCardClick(card.route)}
                  className="p-6 cursor-pointer transition-all duration-300 hover:scale-105 
           bg-gradient-to-br from-gray-200 to-gray-100 
           dark:from-gray-900 dark:to-gray-700 
           border border-gray-300 dark:border-gray-800 
           hover:border-gray-400 dark:hover:border-gray-600"
                >
                  <div className="space-y-4">
                    <div
                      className={cn(
                        "w-12 h-12 rounded-xl flex items-center justify-center",
                        card.iconBg
                      )}
                    >
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-black dark:text-white">
                      {t(card.titleKey)}
                    </h3>
                  </div>
                </Card>
              );
            })}
          </div>


          {/* Chat Messages */}
          {messages.length > 0 || isLoading ? (
            <div className="space-y-4 pb-4">
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
                      <BotIcon className="w-5 h-5 text-white" />
                    </div>
                  )}

                  <div id={`report-${message.id}`} className="relative w-full max-w-3xl">
                    {message.type === "ai" && (message.text.includes("class=\"report") || message.text.includes("class='report") || message.text.includes("report__header")) && (
                      <DownloadPdfButton targetId={`report-${message.id}`} filename="ai_analysis.pdf" />
                    )}
                    <div
                      className={cn(
                        "rounded-2xl px-6 py-4",
                        message.type === "user"
                          ? "bg-gradient-to-br from-[#9810FA] to-[#155DFC] text-white"
                          : "bg-gray-100 dark:bg-[#1E2939] text-gray-900 dark:text-white",
                        message.type === "ai" && styles.kpiHtml
                      )}
                      {...(message.type === "ai"
                        ? {
                            dangerouslySetInnerHTML: {
                              __html:
                                typeof window !== "undefined"
                                  ? DOMPurify.sanitize(message.text, {
                                      USE_PROFILES: { html: true },
                                      ADD_TAGS: ["style"],
                                      ADD_ATTR: ["style", "class"],
                                      FORBID_TAGS: ["script", "iframe", "object", "embed"],
                                    })
                                  : message.text,
                            },
                          }
                        : { children: <p className="whitespace-pre-wrap">{message.text}</p> })}
                    />
                  </div>

                  {message.type === "user" && (
                    <div className="w-10 h-10 rounded-lg bg-gray-600 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0">
                    <BotIcon className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-gray-100 dark:bg-[#1E2939] rounded-2xl px-6 py-4 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              )}

              {/* Invisible div to scroll to */}
              <div ref={messagesEndRef} />
            </div>
          ):(
            <div className="min-h-[135px]"/>
          )}
        </div>
      </div>

      {/* Input Area - Fixed at Bottom */}
      <div className="sticky bottom-0 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-black">
        <div className="max-w-6xl mx-auto p-4">
          {/* Hidden CSV file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              e.target.value = "";
              if (files.length) handleCsvUpload(files);
            }}
          />
          <div className="flex z-10 gap-2 items-center bg-gray-100 dark:bg-[#1E2939] rounded-xl px-4 py-3 border border-gray-300 dark:border-gray-700">
            <Button
              variant="ghost"
              size="icon"
              disabled={isLoading}
              onClick={() => fileInputRef.current?.click()}
              title={t("uploadCsvForKpi")}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-50"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={isLoading}
              placeholder={t("newChatInputPlaceholder")}
              className="flex-1 resize-none overflow-hidden min-h-[20px] max-h-32 bg-transparent border-none text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-500 focus-visible:ring-0 focus-visible:ring-offset-0 disabled:opacity-60"
              rows={1}
            />
            <Button
              onClick={handleSendMessage}
              size="icon"
              disabled={isLoading || !inputValue.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-center text-xs text-gray-500 dark:text-gray-500 mt-2">
            {t("newChatFooterHint")}
          </p>
        </div>
      </div>
    </div>
  );
}
