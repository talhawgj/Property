"use client"

import { useEffect, useState } from "react"
import { Database, Map, BarChart3, Users, Activity, FileText, TrendingUp } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface QueueStats {
  total_jobs: number
  queued_jobs: number
  processing_jobs: number
  completed_jobs: number
  failed_jobs: number
  max_concurrent_jobs: number
  available_slots: number
}

interface AdminDashboardProps {
  setActiveSection?: (section: string) => void
}

export default function AdminDashboard({ setActiveSection }: AdminDashboardProps) {
  const [stats, setStats] = useState<QueueStats | null>(null)
  const [loading, setLoading] = useState(true)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://10.8.0.1:8001"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const headers: HeadersInit = {}
        if (API_KEY) {
          headers["X-API-Key"] = API_KEY
        }

        const response = await fetch(`${API_BASE_URL}/jobs/stats/queue`, {
          headers,
        })
        if (response.ok) {
          const data = await response.json()
          setStats(data)
        }
      } catch (error) {
        console.error("Failed to fetch queue stats:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [API_BASE_URL, API_KEY])

  const totalAnalyses = stats?.total_jobs || 0
  const activeBatchJobs = stats?.processing_jobs || 0
  const activeUsers = 0 // As requested, should be zero at the moment
  const successRate = stats && (stats.completed_jobs + stats.failed_jobs) > 0
    ? ((stats.completed_jobs / (stats.completed_jobs + stats.failed_jobs)) * 100).toFixed(1)
    : "0.0"

  return (
    <div className="p-6 space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="bg-card border-border p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Analyses</p>
              <p className="text-3xl font-bold text-foreground mt-1">
                {loading ? "..." : totalAnalyses}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Total batch jobs</p>
            </div>
            <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
              <Map className="w-6 h-6 text-primary" />
            </div>
          </div>
        </Card>

        <Card className="bg-card border-border p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Active Batch Jobs</p>
              <p className="text-3xl font-bold text-foreground mt-1">
                {loading ? "..." : activeBatchJobs}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {stats ? `${stats.queued_jobs} queued` : "Loading..."}
              </p>
            </div>
            <div className="w-12 h-12 bg-secondary rounded-lg flex items-center justify-center">
              <Database className="w-6 h-6 text-foreground" />
            </div>
          </div>
        </Card>

        <Card className="bg-card border-border p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Active Users</p>
              <p className="text-3xl font-bold text-foreground mt-1">
                {activeUsers}
              </p>
              <p className="text-xs text-muted-foreground mt-1">No active sessions</p>
            </div>
            <div className="w-12 h-12 bg-secondary rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-foreground" />
            </div>
          </div>
        </Card>

        <Card className="bg-card border-border p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
              <p className="text-3xl font-bold text-foreground mt-1">
                {loading ? "..." : `${successRate}%`}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {stats ? `${stats.completed_jobs} completed, ${stats.failed_jobs} failed` : "Loading..."}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-primary" />
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-6">
        {/* Main Actions */}
        <Card className="bg-card border-border p-6">
          <h2 className="text-xl font-bold text-foreground mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <Button 
              onClick={() => setActiveSection?.("batch-analysis")}
              className="h-24 flex-col gap-2 bg-secondary text-secondary-foreground hover:bg-secondary/80"
            >
              <Database className="w-6 h-6" />
              <span>Batch Upload</span>
            </Button>
            <Button 
              onClick={() => setActiveSection?.("operations")}
              variant="outline" 
              className="h-24 flex-col gap-2 border-border"
            >
              <BarChart3 className="w-6 h-6" />
              <span>View Analytics</span>
            </Button>
            <Button 
              onClick={() => setActiveSection?.("logs")}
              variant="outline" 
              className="h-24 flex-col gap-2 border-border"
            >
              <FileText className="w-6 h-6" />
              <span>View Logs</span>
            </Button>
          </div>
        </Card>
      </div>

      {/* System Status */}
      {/* <Card className="bg-card border-border p-6">
        <h2 className="text-xl font-bold text-foreground mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Database</span>
              <Badge className="bg-primary/10 text-primary border-primary/20">Connected</Badge>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: '95%' }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">95% capacity</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Redis Cache</span>
              <Badge className="bg-primary/10 text-primary border-primary/20">Connected</Badge>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: '78%' }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">78% capacity</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">S3 Storage</span>
              <Badge className="bg-primary/10 text-primary border-primary/20">Connected</Badge>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div className="bg-muted-foreground h-2 rounded-full" style={{ width: '62%' }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">62% capacity</p>
          </div>
        </div>
      </Card> */}
    </div>
  )
}
