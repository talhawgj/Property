"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, RefreshCw, ChevronDown } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const LINES = 500

interface LogViewerProps {
  logName: string
}

function LogViewer({ logName }: LogViewerProps) {
  const [offset, setOffset] = useState(0)
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const cancelRef = useRef<AbortController | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  const loadBlock = useCallback(async ({ reset = false } = {}) => {
    if (!logName || loading || (done && !reset)) return

    // Cancel previous request if any
    if (cancelRef.current) cancelRef.current.abort()
    const controller = new AbortController()
    cancelRef.current = controller

    setLoading(true)
    try {
      const currentOffset = reset ? 0 : offset
      const url = `${API_BASE_URL}/logs?name=${logName}&lines=${LINES}&offset=${currentOffset}`
      
      const resp = await fetch(url, {
        headers: {
          "X-API-Key": API_KEY,
        },
        signal: controller.signal,
      })

      if (resp.status === 204 || !resp.ok) {
        if (reset) {
          setContent("")
          setOffset(0)
        }
        setDone(true)
      } else {
        const text = await resp.text()
        if (reset) {
          setContent(text)
          setOffset(LINES)
          setDone(false)
        } else {
          setContent(prev => text + (prev ? "\n" + prev : ""))
          setOffset(prev => prev + LINES)
        }
      }
    } catch (e: any) {
      if (e.name !== "CanceledError" && e.name !== "AbortError") {
        console.error("Error loading logs:", e)
      }
    } finally {
      setLoading(false)
    }
  }, [logName, offset, done, loading, API_BASE_URL, API_KEY])

  // Reset when logName changes
  useEffect(() => {
    if (!logName) return
    setOffset(0)
    setDone(false)
    setContent("")
    loadBlock({ reset: true })
    return () => {
      if (cancelRef.current) cancelRef.current.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logName])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-foreground">
            {logName ? `Log: ${logName}` : "Select a log"}
          </h3>
          {loading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadBlock({ reset: true })}
          disabled={loading || !logName}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Card className="bg-card border-border">
        <div
          className="p-4 overflow-auto whitespace-pre-wrap font-mono text-xs bg-[#0b0b0b] text-[#e6e6e6] rounded-lg"
          style={{ maxHeight: "calc(100vh - 300px)", minHeight: "400px" }}
        >
          {content || (!loading && "No data")}
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="default"
          onClick={() => loadBlock()}
          disabled={loading || done || !logName}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Loading...
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4 mr-2" />
              Load more
            </>
          )}
        </Button>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {done && <span>Start of file reached</span>}
          <span>Loaded: {offset} lines</span>
        </div>
      </div>
    </div>
  )
}

export default function LogsPage() {
  const [logs, setLogs] = useState<string[]>([])
  const [selectedLog, setSelectedLog] = useState<string>("")
  const [loadingLogs, setLoadingLogs] = useState(true)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/logs/list`, {
          headers: {
            "X-API-Key": API_KEY,
          },
        })
        if (response.ok) {
          const data = await response.json()
          setLogs(data.logs || [])
          if (data.logs && data.logs.length > 0) {
            setSelectedLog(data.logs[0])
          }
        }
      } catch (error) {
        console.error("Failed to fetch logs list:", error)
      } finally {
        setLoadingLogs(false)
      }
    }

    fetchLogs()
  }, [API_BASE_URL, API_KEY])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">System Logs</h1>
          <p className="text-muted-foreground mt-1">
            View and monitor system logs in real-time
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          {logs.length} log file{logs.length !== 1 ? "s" : ""} available
        </Badge>
      </div>

      <Card className="bg-card border-border p-6">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-foreground">Select Log:</label>
            <Select value={selectedLog} onValueChange={setSelectedLog} disabled={loadingLogs}>
              <SelectTrigger className="w-64">
                <SelectValue placeholder="Select a log file" />
              </SelectTrigger>
              <SelectContent>
                {logs.map((log) => (
                  <SelectItem key={log} value={log}>
                    {log}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedLog ? (
            <LogViewer key={selectedLog} logName={selectedLog} />
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              {loadingLogs ? "Loading logs..." : "No logs available"}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
