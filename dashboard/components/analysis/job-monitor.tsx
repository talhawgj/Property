"use client"

import React, { useEffect, useState, useRef } from 'react'
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { CheckCircle, XCircle, Loader2, Clock, Download, Trash2 } from "lucide-react"
import { useAnalysis } from "@/contexts/analysis-context"
import { fetchAuthSession } from 'aws-amplify/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://10.8.0.1:8001"

interface JobMonitorProps {
  jobId: string
  onDownload?: (jobId: string) => void
  onRemove?: (jobId: string) => void
  onCancel?: (jobId: string) => void
}

export function JobMonitor({ 
  jobId, 
  onDownload, 
  onRemove,
  onCancel,
}: JobMonitorProps) {
  const { getJob, updateJob } = useAnalysis()
  const [polling, setPolling] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const pollCountRef = useRef(0)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const job = getJob(jobId)

  const handleCancel = async () => {
    if (!onCancel) return
    setCancelling(true)
    try {
      await onCancel(jobId)
    } finally {
      setCancelling(false)
    }
  }

  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    // Don't poll if job is already complete or polling is disabled
    if (!job || !polling || job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      setPolling(false)
      return
    }

    const MAX_POLL_COUNT = 120 // Stop after ~20 minutes (120 * 10s)

    const pollJobStatus = async () => {
      try {
        // Stop polling after max attempts
        if (pollCountRef.current >= MAX_POLL_COUNT) {
          console.log(`Stopped polling job ${jobId} after ${MAX_POLL_COUNT} attempts`)
          setPolling(false)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          return
        }

        pollCountRef.current++

        // Use fetch with correct API URL
        const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        }
        if (API_KEY) {
          headers['x-api-key'] = API_KEY
        }
        
        // Add user ID from Amplify session
        try {
          const session = await fetchAuthSession()
          const userId = session?.tokens?.idToken?.payload?.sub
          if (userId) {
            headers['x-user-id'] = userId as string
          }
        } catch (error) {
          // User not authenticated, continue without x-user-id
          console.warn("No authenticated user session:", error)
        }
        
        const response = await fetch(`${API_BASE_URL}/batch/progress/${jobId}`, {
          headers,
        })
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const jobData = await response.json()
          
        // Handle different response formats
        const status = jobData.status
        const completedRows = jobData.completed_rows || jobData.completedRows || 0
        const totalRows = jobData.total_rows || jobData.totalRows || job.totalRows
        const error = jobData.error_message || jobData.error
        
        updateJob(jobId, {
          status: status,
          completedRows: completedRows,
          totalRows: totalRows,
          error: error,
        })

        // Stop polling if job is complete
        if (status === 'completed' || status === 'failed' || status === 'cancelled') {
          console.log(`Job ${jobId} ${status}, stopping polling`)
          setPolling(false)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      } catch (error: any) {
        console.error('Failed to poll job status:', error)
        
        // Stop polling on critical errors
        const response = error.response
        const shouldStopPolling = 
          response?.status === 404 || // Job not found (killed/deleted)
          response?.status === 410 || // Job gone
          response?.status === 500 || // Server error
          error.code === 'ECONNREFUSED' || // Backend is down
          error.code === 'ERR_NETWORK' || // Network error
          error.message?.includes('Network Error') ||
          error.message?.includes('timeout')
        
        if (shouldStopPolling) {
          console.log(`Stopping polling for job ${jobId} due to error:`, error.message || error.code || response?.status)
          setPolling(false)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          
          // Update job status to failed if it was a 404 (job killed/not found)
          if (response?.status === 404) {
            updateJob(jobId, {
              status: 'failed',
              error: 'Job not found - may have been cancelled or deleted',
            })
          } else {
            updateJob(jobId, {
              status: 'failed',
              error: 'Connection error - backend may be down',
            })
          }
        }
      }
    }

    // Poll every 10 seconds
    intervalRef.current = setInterval(pollJobStatus, 10000)
    
    // Initial poll
    pollJobStatus()

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [jobId, polling, job?.status])

  if (!job) {
    return null
  }

  const progress = job.totalRows > 0 
    ? Math.round((job.completedRows / job.totalRows) * 100) 
    : 0

  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'processing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      case 'queued':
        return <Clock className="w-5 h-5 text-yellow-500" />
      default:
        return null
    }
  }

  const getStatusBadge = () => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      processing: "secondary",
      queued: "outline",
      failed: "destructive",
      cancelled: "destructive",
    }
    
    return (
      <Badge variant={variants[job.status] || "outline"}>
        {job.status.toUpperCase()}
      </Badge>
    )
  }

  return (
    <Card className="border-border bg-card hover:shadow-md transition-shadow">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="shrink-0">
              {getStatusIcon()}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-foreground truncate">
                {job.filename}
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Job ID: {job.jobId.slice(0, 12)}...
              </p>
            </div>
          </div>
          <div className="shrink-0">
            {getStatusBadge()}
          </div>
        </div>

        {/* Progress Bar */}
        {(job.status === 'processing' || job.status === 'queued') && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span className="font-medium">
                {job.completedRows.toLocaleString()} / {job.totalRows.toLocaleString()} rows
              </span>
              <span className="font-semibold">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2 bg-muted" />
          </div>
        )}

        {/* Error Message */}
        {job.status === 'failed' && job.error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-xs text-destructive font-medium">
              {job.error}
            </p>
          </div>
        )}

        {/* Completed Info */}
        {job.status === 'completed' && (
          <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md">
            <p className="text-xs text-green-600 dark:text-green-400 font-medium">
              ✓ Analysis completed! {job.totalRows.toLocaleString()} rows processed.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          {job.status === 'completed' && onDownload && (
            <Button
              size="sm"
              onClick={() => onDownload(job.jobId)}
              className="flex-1"
            >
              <Download className="w-4 h-4 mr-2" />
              Download Results
            </Button>
          )}
          {(job.status === 'queued' || job.status === 'processing') && onCancel && (
            <Button
              size="sm"
              variant="destructive"
              onClick={handleCancel}
              disabled={cancelling}
              className="flex-1"
            >
              {cancelling ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cancelling...
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 mr-2" />
                  Cancel Job
                </>
              )}
            </Button>
          )}
          {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && onRemove && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRemove(job.jobId)}
              className="border-destructive/20 text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Remove
            </Button>
          )}
        </div>

        {/* Timestamp */}
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Started: {new Date(job.createdAt).toLocaleString()}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
