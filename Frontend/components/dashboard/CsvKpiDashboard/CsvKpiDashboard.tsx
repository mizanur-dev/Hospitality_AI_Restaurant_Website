"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import DOMPurify from "dompurify";
import { sendChatMessage, uploadCsv } from "@/services/kpiService";
import styles from "@/components/dashboard/kpiAnalysis/kpiReportStyles.module.css";
import { DownloadPdfButton } from "@/components/dashboard/DownloadPdfButton";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useLanguage } from "@/providers/language-provider";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";

interface KPIData {
  sales?: number;
  labor?: number;
  food?: number;
  prime?: number;
}

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  time: string;
}

interface MetricValues {
  revenue: string;
  laborCost: string;
  foodCost: string;
  primeCost: string;
}

interface CostSlice {
  name: string;
  value: number;
  color: string;
}

function parseCurrencyToNumber(value: string): number {
  const n = parseFloat(value.replace(/[^0-9.-]/g, ""));
  return isNaN(n) ? NaN : n;
}
function formatCurrency(n: number) {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
function formatPercent(n: number) {
  return `${n.toFixed(1)}%`;
}
function getNow() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function extractKPIData(message: string): KPIData {
  const patterns: Record<keyof KPIData, RegExp> = {
    sales: /(total\s*sales|sales)\s*:\s*([^\n]+)/i,
    labor: /(labor\s*cost|labor)\s*:\s*([^\n]+)/i,
    food: /(food\s*cost|food)\s*:\s*([^\n]+)/i,
    prime: /(prime\s*cost|prime)\s*:\s*([^\n]+)/i,
  };
  const out: KPIData = {};
  (Object.entries(patterns) as [keyof KPIData, RegExp][]).forEach(([key, rx]) => {
    const match = message.match(rx);
    if (match?.[2]) {
      const v = parseCurrencyToNumber(match[2]);
      if (!isNaN(v)) out[key] = v;
    }
  });
  return out;
}

const revenueData = [
  { week: "Week 1", revenue: 28500 },
  { week: "Week 2", revenue: 31200 },
  { week: "Week 3", revenue: 30800 },
  { week: "Week 4", revenue: 34080 },
];

const weeklyData = [
  { day: "Mon", sales: 3200 },
  { day: "Tue", sales: 2800 },
  { day: "Wed", sales: 3100 },
  { day: "Thu", sales: 3400 },
  { day: "Fri", sales: 4200 },
  { day: "Sat", sales: 5100 },
  { day: "Sun", sales: 4800 },
];

const kpiRadarData = [
  { metric: "Labor", current: 75, target: 80 },
  { metric: "Food", current: 82, target: 80 },
  { metric: "Beverage", current: 78, target: 80 },
  { metric: "RevPASH", current: 88, target: 85 },
  { metric: "Turnover", current: 70, target: 80 },
  { metric: "Satisfaction", current: 92, target: 90 },
];

const defaultCostSlices: CostSlice[] = [
  { name: "Labor", value: 32.4, color: "#6366f1" },
  { name: "Food", value: 28.2, color: "#8b5cf6" },
  { name: "Overhead", value: 22.4, color: "#f59e0b" },
  { name: "Profit", value: 17.0, color: "#10b981" },
];

const revenueConfig: ChartConfig = {
  revenue: { label: "Revenue", color: "#6366f1" },
};

const weeklyConfig: ChartConfig = {
  sales: { label: "Sales", color: "#6366f1" },
};

const radarConfig: ChartConfig = {
  current: { label: "Current", color: "#6366f1" },
  target: { label: "Target", color: "#10b981" },
};

const VARIANT_STYLES = {
  good: {
    bar: "from-emerald-400 to-green-300",
    value: "from-emerald-500 to-emerald-700",
  },
  warning: {
    bar: "from-amber-400 to-yellow-300",
    value: "from-amber-500 to-amber-700",
  },
  alert: {
    bar: "from-red-500 to-red-300",
    value: "from-red-500 to-red-700",
  },
};

function MetricCard({
  label,
  value,
  change,
  changePositive,
  variant,
}: {
  label: string;
  value: string;
  change: string;
  changePositive: boolean;
  variant: "good" | "warning" | "alert";
}) {
  const s = VARIANT_STYLES[variant];
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-2 hover:shadow-xl hover:shadow-indigo-100/40">
      <div className={`absolute top-0 inset-x-0 h-1 bg-gradient-to-r ${s.bar}`} />
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.05),transparent_65%)]" />
      <p className="relative z-10 text-[0.7rem] font-semibold uppercase tracking-widest text-slate-400">
        {label}
      </p>
      <p
        className={`relative z-10 my-2 bg-gradient-to-br ${s.value} bg-clip-text text-[2.6rem] font-black leading-none text-transparent`}
      >
        {value}
      </p>
      <div
        className={`relative z-10 flex items-center gap-1 text-sm font-semibold ${changePositive ? "text-emerald-500" : "text-red-500"
          }`}
      >
        {changePositive ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7 14l5-5 5 5z" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7 10l5 5 5-5z" />
          </svg>
        )}
        {change}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:shadow-indigo-100/30">
      <div className="mb-5 flex items-center gap-3">
        <span className="h-5 w-1 rounded-full bg-gradient-to-b from-indigo-500 to-purple-500" />
        <h3 className="text-base font-bold text-slate-800">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const safeHtml =
    typeof window !== "undefined"
      ? DOMPurify.sanitize(msg.content, {
          USE_PROFILES: { html: true },
          ADD_ATTR: ["style", "class"],
          FORBID_TAGS: ["script", "iframe", "object", "embed"],
        })
      : msg.content;
  const isReportHtml =
    !msg.isUser &&
    (safeHtml.includes('class="report') || safeHtml.includes("class='report"));
  return (
    <div className={`flex flex-col ${msg.isUser ? "items-end" : "items-start"}`}>
      <div id={`report-${msg.id}`}
        className={`relative max-w-[85%] rounded-2xl text-sm leading-relaxed ${
          msg.isUser
            ? "px-4 py-3 bg-gradient-to-br from-indigo-500 to-purple-600 text-white"
            : isReportHtml
              ? "p-0 bg-transparent border-0 shadow-none"
              : "px-4 py-3 border border-slate-100 bg-slate-50 text-slate-700 shadow-sm"
        } ${!msg.isUser ? styles.kpiHtml : ""}`}
      >
        {isReportHtml && (
          <DownloadPdfButton targetId={`report-${msg.id}`} filename="kpi_report.pdf" />
        )}
        <div dangerouslySetInnerHTML={{ __html: safeHtml }} />
      </div>
      <span className="mt-1 text-[0.7rem] text-slate-400">{msg.time}</span>
    </div>
  );
}

const RADIAN = Math.PI / 180;
function renderCustomLabel({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
}) {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  if (percent < 0.05) return null;
  return (
    <text
      x={x}
      y={y}
      fill="#fff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
    >
      {`${(percent * 100).toFixed(1)}%`}
    </text>
  );
}

// INITIAL_MESSAGE created inside component to use t()

export default function KPIDashboard() {
  const { language, t } = useLanguage();
  const INITIAL_MESSAGE: Message = {
    id: "0",
    content: t("welcomeMessage"),
    isUser: false,
    time: t("justNow"),
  };
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [metrics, setMetrics] = useState<MetricValues>({
    revenue: "$124,580",
    laborCost: "32.4%",
    foodCost: "28.2%",
    primeCost: "60.6%",
  });

  const [costSlices, setCostSlices] = useState<CostSlice[]>(defaultCostSlices);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = useCallback((content: string, isUser: boolean) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), content, isUser, time: getNow() },
    ]);
  }, []);

  const handleComprehensiveAnalysis = useCallback(
    (message: string): boolean => {
      const kpi = extractKPIData(message);
      const { sales, labor, food } = kpi;
      if (
        typeof sales !== "number" ||
        typeof labor !== "number" ||
        typeof food !== "number"
      )
        return false;

      const prime = typeof kpi.prime === "number" ? kpi.prime : labor + food;
      const laborPct = (labor / sales) * 100;
      const foodPct = (food / sales) * 100;
      const primePct = (prime / sales) * 100;
      const profit = sales - prime;
      const profitPct = (profit / sales) * 100;
      const overheadPct = Math.max(0, 100 - (laborPct + foodPct + profitPct));

      setMetrics({
        revenue: formatCurrency(sales),
        laborCost: formatPercent(laborPct),
        foodCost: formatPercent(foodPct),
        primeCost: formatPercent(primePct),
      });

      setCostSlices([
        { name: t("labor"), value: parseFloat(laborPct.toFixed(1)), color: "#6366f1" },
        { name: t("food"), value: parseFloat(foodPct.toFixed(1)), color: "#8b5cf6" },
        { name: t("overhead"), value: parseFloat(overheadPct.toFixed(1)), color: "#f59e0b" },
        { name: t("profit"), value: parseFloat(profitPct.toFixed(1)), color: "#10b981" },
      ]);

      return true;
    },
    []
  );

  const sendMessage = useCallback(async () => {
    const msg = input.trim();
    if (!msg || isLoading) return;

    addMessage(msg, true);
    setInput("");

    if (/run\s+comprehensive\s+analysis/i.test(msg)) {
      handleComprehensiveAnalysis(msg);
    }

    setIsLoading(true);
    try {
      const data = await sendChatMessage(msg, language);
      addMessage(data.html_response, false);
    } catch (err) {
      addMessage(`❌ ${t("error")}: ${(err as Error).message}`, false);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, addMessage, handleComprehensiveAnalysis]);

  const handleCsvUpload = useCallback(
    async (files: File[]) => {
      if (!files.length || isLoading) return;
      setIsLoading(true);
      addMessage(
        files.length === 1
          ? `${t("uploadedCsv")} ${files[0].name}`
          : `${t("uploadedCsvs")} ${files.map((f) => f.name).join(", ")}`,
        true
      );
      try {
        const formData = new FormData();
        formData.append("required_csv", files[0]);
        if (files[1]) formData.append("optional_csv", files[1]);
        const data = await uploadCsv(formData, language);
        addMessage(data.html_response, false);
      } catch (err) {
        addMessage(`❌ ${t("csvError")} ${(err as Error).message}`, false);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, addMessage]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => setMessages([INITIAL_MESSAGE]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20 font-sans antialiased">
      {/* Ambient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-32 h-96 w-96 animate-[pulse_6s_ease-in-out_infinite] rounded-full bg-indigo-200/25 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-80 w-80 animate-[pulse_8s_ease-in-out_infinite_1s] rounded-full bg-purple-200/20 blur-3xl" />
      </div>

      <main className="relative z-10 mx-auto max-w-7xl px-6 py-10">
        <div className="text-center mb-12">
          <h1 className="bg-gradient-to-r from-[#C27AFF] via-[#51A2FF] to-[#C27AFF] bg-clip-text text-transparent text-4xl font-bold text-center mb-4">
            {t("kpiDashboard")}
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-xl whitespace-pre-line">
            {t("kpiDashboardSubtitle")}
          </p>
        </div>

        {/* ── Quick Stats ── */}
        {/* <div className="mb-8 flex flex-wrap gap-3">
          {[
            {
              dot: "bg-emerald-500 shadow-emerald-400/60",
              label: "4 KPIs On Target",
            },
            {
              dot: "bg-amber-400 shadow-amber-300/60",
              label: "2 KPIs Need Attention",
            },
            { dot: "bg-red-500 shadow-red-400/60", label: "1 KPI Critical" },
          ].map(({ dot, label }) => (
            <span
              key={label}
              className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/90 px-4 py-1.5 text-xs font-semibold text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <span
                className={`h-2 w-2 rounded-full shadow-[0_0_6px] ${dot}`}
              />
              {label}
            </span>
          ))}
        </div> */}

        {/* ── Metric Cards ── */}
        <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label={t("revenue")}
            value={metrics.revenue}
            change={t("vsLastPeriod")}
            changePositive
            variant="good"
          />
          <MetricCard
            label={t("laborCostPercent")}
            value={metrics.laborCost}
            change={t("vsTarget")}
            changePositive={false}
            variant="warning"
          />
          <MetricCard
            label={t("foodCostPercent")}
            value={metrics.foodCost}
            change={t("vsFoodTarget")}
            changePositive
            variant="good"
          />
          <MetricCard
            label={t("primeCostPercent")}
            value={metrics.primeCost}
            change={t("onTarget")}
            changePositive
            variant="good"
          />
        </div>

        {/* ── Charts Row 1 ── */}
        <div className="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {/* Revenue Trend — ChartContainer + ChartTooltip */}
          <ChartCard title={t("revenueTrend")}>
            <ChartContainer config={revenueConfig} className="h-56 w-full">
              <LineChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(value) => [
                        `$${Number(value).toLocaleString()}`,
                        "Revenue",
                      ]}
                    />
                  }
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="var(--color-revenue)"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "var(--color-revenue)", strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ChartContainer>
          </ChartCard>

          {/* Cost Distribution — plain Recharts PieChart (no ChartContainer needed) */}
          <ChartCard title={t("costDistribution")}>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={costSlices}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    dataKey="value"
                    labelLine={false}
                    label={renderCustomLabel}
                  >
                    {costSlices.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [
                      `${value.toFixed(1)}%`,
                      "",
                    ]}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid #e2e8f0",
                      fontSize: 12,
                    }}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{
                      fontSize: 12,
                      color: "#64748b",
                      paddingTop: 8,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>

        {/* ── Charts Row 2 ── */}
        <div className="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {/* Weekly Performance — ChartContainer + ChartTooltip */}
          <ChartCard title={t("weeklyPerformance")}>
            <ChartContainer config={weeklyConfig} className="h-56 w-full">
              <BarChart data={weeklyData} barSize={28}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e2e8f0"
                  vertical={false}
                />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(value) => [
                        `$${Number(value).toLocaleString()}`,
                        "Sales",
                      ]}
                    />
                  }
                />
                <Bar
                  dataKey="sales"
                  fill="var(--color-sales)"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ChartContainer>
          </ChartCard>

          {/* KPI Comparison — ChartContainer + ChartLegend + ChartTooltip */}
          <ChartCard title={t("kpiComparison")}>
            <ChartContainer config={radarConfig} className="h-56 w-full">
              <RadarChart data={kpiRadarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fontSize: 9, fill: "#94a3b8" }}
                />
                <Radar
                  name="Current"
                  dataKey="current"
                  stroke="var(--color-current)"
                  fill="var(--color-current)"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Radar
                  name="Target"
                  dataKey="target"
                  stroke="var(--color-target)"
                  fill="var(--color-target)"
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
                <ChartLegend content={<ChartLegendContent />} />
                <ChartTooltip content={<ChartTooltipContent />} />
              </RadarChart>
            </ChartContainer>
          </ChartCard>
        </div>

        {/* ── Chat Section ── */}
        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-sm">
          {/* header */}
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-sm">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
                </svg>
              </span>
              <h3 className="font-bold text-slate-800">{t("aiInsights")}</h3>
            </div>
            <button
              onClick={clearChat}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            >
              {t("clear")}
            </button>
          </div>

          {/* messages */}
          <div className="flex h-72 flex-col gap-3 overflow-y-auto px-6 py-5">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {isLoading && (
              <div className="flex items-start">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 shadow-sm">
                  <div className="flex gap-1">
                    {[0, 150, 300].map((d) => (
                      <span
                        key={d}
                        className="h-2 w-2 animate-bounce rounded-full bg-indigo-400"
                        style={{ animationDelay: `${d}ms` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* input */}
          <div className="border-t border-slate-100 px-6 py-4">
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
            <div className="flex items-end gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 transition focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                title="Upload CSV for KPI analysis"
                className="flex-shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-200 hover:text-indigo-600 disabled:opacity-50"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t("askAboutKpis")}
                rows={1}
                className="flex-1 resize-none bg-transparent text-sm text-slate-700 placeholder-slate-400 focus:outline-none"
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-indigo-300/40 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("ask")}
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}