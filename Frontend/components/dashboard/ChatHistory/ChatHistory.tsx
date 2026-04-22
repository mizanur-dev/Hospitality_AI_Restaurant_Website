"use client"

import { useState } from "react"
import { Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { useLanguage } from "@/providers/language-provider"

import { Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface ChatHistoryItem {
  id: number
  title: string
  description: string
  date: string
  type: string
}

const initialChatHistory: ChatHistoryItem[] = [
  {
    id: 1,
    title: "Beverage Management",
    description: "Hello! I'm here to help you optimize your bar operations. Ask me about liquor costs.",
    date: "28-2-26",
    type: "Beverage Management"
  },
  {
    id: 2,
    title: "Staffing Optimization",
    description: "inventory management, pricing strategies, or upload data for analysis.",
    date: "28-2-26",
    type: "Staffing Optimization"
  },
  {
    id: 3,
    title: "KPI Analysis",
    description: "Atlantic Salmon",
    date: "28-2-26",
    type: "KPI Analysis"
  },
  {
    id: 4,
    title: "KPI Analysis",
    description: "Roma Tomatoes",
    date: "28-2-26",
    type: "KPI Analysis"
  },
  {
    id: 5,
    title: "KPI Analysis",
    description: "Extra Virgin Olive Oil",
    date: "28-2-26",
    type: "KPI Analysis"
  },
]

export default function ChatHistory() {
  const { t } = useLanguage()
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>(initialChatHistory)
  const [filterType, setFilterType] = useState<string>("all")
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const filteredHistory = filterType === "all" 
    ? chatHistory 
    : chatHistory.filter(item => item.type === filterType)

  const handleDelete = (id: number) => {
    setChatHistory(chatHistory.filter(item => item.id !== id))
    setDeleteId(null)
  }

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 sm:p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-purple-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
          {t("chatHistoryTitle")}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base">
          {t("chatHistorySubtitle")}
        </p>
      </div>

      {/* Filter */}
      <div className="flex justify-end">
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-[180px] bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700">
            <SelectValue placeholder={t("allTypes")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("allTypes")}</SelectItem>
            <SelectItem value="KPI Analysis">KPI Analysis</SelectItem>
            <SelectItem value="Beverage Management">Beverage Management</SelectItem>
            <SelectItem value="Staffing Optimization">Staffing Optimization</SelectItem>
            <SelectItem value="Menu Engineering">Menu Engineering</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block bg-white dark:bg-transparent rounded-xl overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-200 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-800 border-b border-gray-300 dark:border-gray-700">
              <TableHead className="text-gray-900 dark:text-gray-300 font-semibold w-16">#</TableHead>
              <TableHead className="text-gray-900 dark:text-gray-300 font-semibold">{t("titleAndDescription")}</TableHead>
              <TableHead className="text-gray-900 dark:text-gray-300 font-semibold text-right">{t("date")}</TableHead>
              <TableHead className="text-gray-900 dark:text-gray-300 font-semibold w-20"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredHistory.map((item, index) => (
              <TableRow
                key={item.id}
                className="bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-b border-gray-300 dark:border-gray-700 last:border-0"
              >
                <TableCell className="text-gray-900 dark:text-gray-300 font-medium">{index + 1}</TableCell>
                <TableCell>
                  <div className="space-y-1">
                    <p className="text-gray-900 dark:text-white font-medium">{item.title}</p>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">{item.description}</p>
                  </div>
                </TableCell>
                <TableCell className="text-gray-900 dark:text-gray-300 text-right">{item.date}</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteId(item.id)}
                    className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden space-y-3">
        {filteredHistory.map((item, index) => (
          <Card
            key={item.id}
            className="bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-700 p-4 space-y-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex gap-3 flex-1">
                <div className="w-8 h-8 rounded-lg bg-gray-200 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                  <span className="text-gray-900 dark:text-gray-300 font-semibold text-sm">{index + 1}</span>
                </div>
                <div className="space-y-1 flex-1 min-w-0">
                  <p className="text-gray-900 dark:text-white font-medium text-sm">{item.title}</p>
                  <p className="text-gray-600 dark:text-gray-400 text-xs line-clamp-2">{item.description}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setDeleteId(item.id)}
                className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-500/10 flex-shrink-0 h-8 w-8"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex justify-end">
              <span className="text-gray-600 dark:text-gray-400 text-xs">{item.date}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredHistory.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">{t("noChatHistory")}</p>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-gray-900 dark:text-white">
              Delete Chat History
            </AlertDialogTitle>
            <AlertDialogDescription className="text-gray-600 dark:text-gray-400">
              Are you sure you want to delete this chat? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-700">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && handleDelete(deleteId)}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}