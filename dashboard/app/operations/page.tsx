"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FileText, Clock, Users, AlertTriangle, CheckCircle, XCircle, Loader2, Upload } from "lucide-react"
import { getCurrentUserInfo } from "@/lib/auth/roles"

interface BatchJob {
  job_id: string
  user_id: string
  username: string
  email?: string
  status: "queued" | "processing" | "completed" | "failed" | "cancelled"
  priority: "low" | "normal" | "high"
  total_rows: number
  completed_rows: number
  failed_rows: number
  filename: string
  file_path?: string
  dry_run?: boolean
  column_mapping?: Record<string, any>
  lat_column?: string
  lon_column?: string
  error_message?: string
  result_url?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

interface QueueStats {
  total_jobs: number
  queued_jobs: number
  processing_jobs: number
  completed_jobs: number
  failed_jobs: number
  max_concurrent_jobs: number
  available_slots: number
}

export default function OperationsPage() {
  const [jobs, setJobs] = useState<BatchJob[]>([])
  const [stats, setStats] = useState<QueueStats | null>(null)
  const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null)
  const [loading, setLoading] = useState(true)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  useEffect(() => {
    fetchUserInfo()
    fetchData()
    
    // Poll for updates every 2 minutes to reduce database load
    const interval = setInterval(fetchData, 120000)
    
    // Stop polling when page is not visible
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchData() // Refresh when page becomes visible
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  const fetchUserInfo = async () => {
    try {
      const info = await getCurrentUserInfo()
      setUserInfo(info)
      setIsAdmin(info?.role === 'admin')
    } catch (error) {
      console.error("Failed to fetch user info:", error)
    }
  }

  const fetchData = async () => {
    try {
      // Validate API key before making requests
      if (!API_KEY) {
        console.error("API key is not configured")
        setLoading(false)
        return
      }

      const info = userInfo || await getCurrentUserInfo()
      
      // Fetch all jobs (admin view) or user's jobs
      const jobsEndpoint = isAdmin || info?.role === 'admin' 
        ? `${API_BASE_URL}/batch/jobs`
        : `${API_BASE_URL}/api/jobs/user/me`
      
      const jobsResponse = await fetch(jobsEndpoint, {
        headers: {
          "x-api-key": API_KEY,
          "x-user-id": info?.userId || "",
        },
      })
      
      if (jobsResponse.ok) {
        const jobsData = await jobsResponse.json()
        setJobs(jobsData)
      } else if (jobsResponse.status === 401 || jobsResponse.status === 403) {
        console.error("API authentication failed - check API key")
      }

      // Fetch queue stats
      const statsResponse = await fetch(`${API_BASE_URL}/jobs/stats/queue`, {
        headers: {
          "x-api-key": API_KEY,
        },
      })
      
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      } else if (statsResponse.status === 401 || statsResponse.status === 403) {
        console.error("API authentication failed for stats - check API key")
      }
      
      setLastUpdated(new Date())
      setLoading(false)
    } catch (error) {
      console.error("Failed to fetch data:", error)
      setLoading(false)
    }
  }

  const cancelJob = async (jobId: string) => {
    try {
      if (!API_KEY) {
        console.error("API key is not configured")
        return
      }

      const response = await fetch(`${API_BASE_URL}/batch/cancel/${jobId}`, {
        method: "POST",
        headers: {
          "x-api-key": API_KEY,
          "x-user-id": userInfo?.userId || "",
        },
      })

      if (response.ok) {
        await fetchData()
        if (selectedJob?.job_id === jobId) {
          setSelectedJob(null)
        }
      } else if (response.status === 401 || response.status === 403) {
        console.error("API authentication failed - check API key")
      }
    } catch (error) {
      console.error("Failed to cancel job:", error)
    }
  }

  const downloadResults = async (jobId: string) => {
    try {
      if (!API_KEY) {
        console.error("API key is not configured")
        return
      }

      const response = await fetch(`${API_BASE_URL}/batch/download/${jobId}`, {
        headers: {
          "x-api-key": API_KEY,
        },
      })

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          console.error("API authentication failed - check API key")
        }
        throw new Error(`Download failed: ${response.status} ${response.statusText}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `batch_results_${jobId}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Failed to download results:", error)
      alert("Failed to download results. Please try again.")
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "processing":
        return "bg-white text-black border border-white"
      case "queued":
        return "bg-black text-white border border-neutral-800"
      case "completed":
        return "bg-neutral-200 text-black border border-neutral-200"
      case "failed":
        return "bg-black text-neutral-400 border border-neutral-800"
      case "cancelled":
        return "bg-black text-neutral-600 border border-neutral-800"
      default:
        return "bg-black text-neutral-600 border border-neutral-800"
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-white text-black border border-white"
      case "normal":
        return "bg-neutral-800 text-white border border-neutral-700"
      case "low":
        return "bg-black text-neutral-400 border border-neutral-800"
      default:
        return "bg-black text-neutral-400 border border-neutral-800"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "processing":
        return <Loader2 className="w-4 h-4 animate-spin" />
      case "queued":
        return <Clock className="w-4 h-4" />
      case "completed":
        return <CheckCircle className="w-4 h-4" />
      case "failed":
        return <XCircle className="w-4 h-4" />
      case "cancelled":
        return <XCircle className="w-4 h-4" />
      default:
        return <AlertTriangle className="w-4 h-4" />
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A"
    return new Date(dateString).toLocaleString()
  }

  const calculateProgress = (job: BatchJob) => {
    if (job.total_rows === 0) return 0
    return Math.round((job.completed_rows / job.total_rows) * 100)
  }

  // Filter jobs by status
  const processingJobs = jobs.filter(job => job.status === 'processing')
  const queuedJobs = jobs.filter(job => job.status === 'queued')
  const completedJobs = jobs.filter(job => job.status === 'completed')
  const failedCancelledJobs = jobs.filter(job => job.status === 'failed' || job.status === 'cancelled')

  const renderJobCard = (job: BatchJob) => (
    <Card
      key={job.job_id}
      className="bg-neutral-900 border-neutral-800 hover:border-neutral-600 transition-colors cursor-pointer"
      onClick={() => setSelectedJob(job)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-sm font-bold text-white tracking-wider truncate">
              {job.filename}
            </CardTitle>
            <p className="text-xs text-neutral-400 font-mono truncate">{job.job_id}</p>
          </div>
          <div className="flex items-center gap-2 ml-2">
            {getStatusIcon(job.status)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2 flex-wrap">
          <Badge className={getStatusColor(job.status)}>
            {job.status.toUpperCase()}
          </Badge>
          <Badge className={getPriorityColor(job.priority)}>
            {job.priority.toUpperCase()}
          </Badge>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <Users className="w-3 h-3" />
            <span>{job.username}</span>
          </div>
          {job.email && (
            <div className="flex items-center gap-2 text-xs text-neutral-400">
              <span className="text-neutral-500">✉</span>
              <span className="truncate">{job.email}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <FileText className="w-3 h-3" />
            <span>{job.total_rows} rows</span>
            {job.completed_rows > 0 && (
              <span className="text-neutral-500">
                • {job.completed_rows} completed
              </span>
            )}
            {job.failed_rows > 0 && (
              <span className="text-red-400">
                • {job.failed_rows} failed
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <Clock className="w-3 h-3" />
            <span>{formatDate(job.created_at)}</span>
          </div>
        </div>

        {job.status === "processing" && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-neutral-400">Progress</span>
              <span className="text-white font-mono">{calculateProgress(job)}%</span>
            </div>
            <div className="w-full bg-neutral-800 rounded-full h-2">
              <div
                className="bg-white h-2 rounded-full transition-all duration-300"
                style={{ width: `${calculateProgress(job)}%` }}
              ></div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wider">BATCH ANALYSIS OPERATIONS</h1>
          <p className="text-sm text-neutral-400">
            Monitor and manage batch analysis jobs
            {lastUpdated && (
              <span className="ml-2">• Last updated: {lastUpdated.toLocaleTimeString()}</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={fetchData} 
            className="bg-white hover:bg-neutral-200 text-black"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-neutral-900 border-neutral-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-neutral-400 tracking-wider">PROCESSING</p>
                  <p className="text-2xl font-bold text-white font-mono">{stats.processing_jobs}</p>
                </div>
                <Loader2 className="w-8 h-8 text-white" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-neutral-400 tracking-wider">QUEUED</p>
                  <p className="text-2xl font-bold text-white font-mono">{stats.queued_jobs}</p>
                </div>
                <Clock className="w-8 h-8 text-neutral-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-neutral-400 tracking-wider">COMPLETED</p>
                  <p className="text-2xl font-bold text-white font-mono">{stats.completed_jobs}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-neutral-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-neutral-400 tracking-wider">AVAILABLE SLOTS</p>
                  <p className="text-2xl font-bold text-white font-mono">
                    {stats.available_slots}/{stats.max_concurrent_jobs}
                  </p>
                </div>
                <Upload className="w-8 h-8 text-neutral-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <Card className="bg-neutral-900 border-neutral-800">
          <CardContent className="p-8 text-center">
            <FileText className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
            <p className="text-neutral-400">No batch analysis jobs found</p>
            <p className="text-sm text-neutral-500 mt-2">
              Submit a batch analysis to see it here
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {/* Processing Jobs Section */}
          {processingJobs.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Loader2 className="w-5 h-5 text-white animate-spin" />
                <h2 className="text-lg font-bold text-white tracking-wider">PROCESSING</h2>
                <Badge className="bg-white text-black font-mono">
                  {processingJobs.length}
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {processingJobs.map(renderJobCard)}
              </div>
            </div>
          )}

          {/* Queued Jobs Section */}
          {queuedJobs.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Clock className="w-5 h-5 text-neutral-400" />
                <h2 className="text-lg font-bold text-white tracking-wider">QUEUED</h2>
                <Badge className="bg-neutral-800 text-white font-mono border border-neutral-700">
                  {queuedJobs.length}
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {queuedJobs.map(renderJobCard)}
              </div>
            </div>
          )}

          {/* Completed Jobs Section */}
          {completedJobs.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle className="w-5 h-5 text-neutral-400" />
                <h2 className="text-lg font-bold text-white tracking-wider">COMPLETED</h2>
                <Badge className="bg-neutral-200 text-black font-mono">
                  {completedJobs.length}
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {completedJobs.map(renderJobCard)}
              </div>
            </div>
          )}

          {/* Failed/Cancelled Jobs Section */}
          {failedCancelledJobs.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <XCircle className="w-5 h-5 text-neutral-400" />
                <h2 className="text-lg font-bold text-white tracking-wider">FAILED / CANCELLED</h2>
                <Badge className="bg-black text-neutral-400 font-mono border border-neutral-800">
                  {failedCancelledJobs.length}
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {failedCancelledJobs.map(renderJobCard)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Job Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="bg-neutral-900 border-neutral-800 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl font-bold text-white tracking-wider">
                  {selectedJob.filename}
                </CardTitle>
                <p className="text-sm text-neutral-400 font-mono">{selectedJob.job_id}</p>
              </div>
              <Button
                variant="ghost"
                onClick={() => setSelectedJob(null)}
                className="text-neutral-400 hover:text-white"
              >
                ✕
              </Button>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-neutral-300 tracking-wider mb-2">JOB STATUS</h3>
                    <div className="flex gap-2">
                      <Badge className={getStatusColor(selectedJob.status)}>
                        {selectedJob.status.toUpperCase()}
                      </Badge>
                      <Badge className={getPriorityColor(selectedJob.priority)}>
                        {selectedJob.priority.toUpperCase()}
                      </Badge>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-neutral-300 tracking-wider mb-2">JOB DETAILS</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-neutral-400">User:</span>
                        <span className="text-white">{selectedJob.username}</span>
                      </div>
                      {selectedJob.email && (
                        <div className="flex justify-between">
                          <span className="text-neutral-400">Email:</span>
                          <span className="text-white text-xs truncate max-w-[200px]">{selectedJob.email}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-neutral-400">Total Rows:</span>
                        <span className="text-white font-mono">{selectedJob.total_rows}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-400">Completed:</span>
                        <span className="text-white font-mono">{selectedJob.completed_rows}</span>
                      </div>
                      {selectedJob.failed_rows > 0 && (
                        <div className="flex justify-between">
                          <span className="text-neutral-400">Failed:</span>
                          <span className="text-red-400 font-mono">{selectedJob.failed_rows}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-neutral-400">Created:</span>
                        <span className="text-white font-mono text-xs">{formatDate(selectedJob.created_at)}</span>
                      </div>
                      {selectedJob.started_at && (
                        <div className="flex justify-between">
                          <span className="text-neutral-400">Started:</span>
                          <span className="text-white font-mono text-xs">{formatDate(selectedJob.started_at)}</span>
                        </div>
                      )}
                      {selectedJob.completed_at && (
                        <div className="flex justify-between">
                          <span className="text-neutral-400">Completed:</span>
                          <span className="text-white font-mono text-xs">{formatDate(selectedJob.completed_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {(selectedJob.lat_column || selectedJob.lon_column) && (
                    <div>
                      <h3 className="text-sm font-medium text-neutral-300 tracking-wider mb-2">COLUMN MAPPING</h3>
                      <div className="space-y-2 text-sm">
                        {selectedJob.lat_column && (
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Latitude:</span>
                            <span className="text-white">{selectedJob.lat_column}</span>
                          </div>
                        )}
                        {selectedJob.lon_column && (
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Longitude:</span>
                            <span className="text-white">{selectedJob.lon_column}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  {selectedJob.status === "processing" && (
                    <div>
                      <h3 className="text-sm font-medium text-neutral-300 tracking-wider mb-2">PROGRESS</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-neutral-400">Completion</span>
                          <span className="text-white font-mono">{calculateProgress(selectedJob)}%</span>
                        </div>
                        <div className="w-full bg-neutral-800 rounded-full h-3">
                          <div
                            className="bg-white h-3 rounded-full transition-all duration-300"
                            style={{ width: `${calculateProgress(selectedJob)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  )}

                  {selectedJob.error_message && (
                    <div>
                      <h3 className="text-sm font-medium text-neutral-400 tracking-wider mb-2">ERROR MESSAGE</h3>
                      <p className="text-sm text-neutral-300 bg-neutral-900 p-3 rounded border border-neutral-800">
                        {selectedJob.error_message}
                      </p>
                    </div>
                  )}

                  {selectedJob.result_url && selectedJob.status === "completed" && (
                    <div>
                      <h3 className="text-sm font-medium text-neutral-300 tracking-wider mb-2">RESULT</h3>
                      <Button 
                        onClick={() => downloadResults(selectedJob.job_id)}
                        className="w-full bg-white hover:bg-neutral-200 text-black"
                      >
                        Download Results
                      </Button>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-neutral-800">
                {(selectedJob.status === "queued" || selectedJob.status === "processing") && (
                  <Button
                    onClick={() => cancelJob(selectedJob.job_id)}
                    className="bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800"
                  >
                    Cancel Job
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => setSelectedJob(null)}
                  className="border-neutral-800 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-300 bg-transparent"
                >
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
