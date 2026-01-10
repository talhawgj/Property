"use client"

import React, { useState, useEffect } from 'react'
import { Upload, FileSpreadsheet, AlertCircle, Loader2, CheckCircle2, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import api from '@/lib/api'
import * as XLSX from 'xlsx'
import { useAnalysis } from '@/contexts/analysis-context'
import { JobMonitor } from './job-monitor'
import { getCurrentUserInfo } from '@/lib/auth/roles'



interface ColumnMapping {
  latitude: string
  longitude: string
}

interface AnalysisResult {
  [key: string]: any
}

// Helper function to safely convert error responses to strings
const formatErrorMessage = (error: any): string => {
  if (typeof error === 'string') {
    return error
  }
  
  if (Array.isArray(error)) {
    // Handle validation error arrays
    return error.map(err => {
      if (typeof err === 'object' && err.msg) {
        const location = err.loc ? ` (${err.loc.join(' -> ')})` : ''
        return `${err.msg}${location}`
      }
      return JSON.stringify(err)
    }).join('; ')
  }
  
  if (typeof error === 'object') {
    // Handle error objects
    if (error.msg) {
      return error.msg
    }
    if (error.message) {
      return error.message
    }
    return JSON.stringify(error)
  }
  
  return String(error)
}

export function BatchAnalysis() {
  const { activeJobs, addJob, removeJob, getJob, pendingBatchFile, setPendingBatchFile } = useAnalysis()
  const [file, setFile] = useState<File | null>(null)
  const [fileHeaders, setFileHeaders] = useState<string[]>([])
  const [columnMapping, setColumnMapping] = useState<ColumnMapping>({ latitude: '', longitude: '' })
  const expectedColumns = ['latitude', 'longitude']
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [error, setError] = useState<string>('')
  const [results, setResults] = useState<AnalysisResult[]>([])
  const [isUploaded, setIsUploaded] = useState<boolean>(false)
  const [userInfo, setUserInfo] = useState<any>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://10.8.0.1:8001"
  const PROPERTY_API_URL = process.env.NEXT_PUBLIC_PROPERTY_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  useEffect(() => {
    const loadUserInfo = async () => {
      try {
        const info = await getCurrentUserInfo()
        setUserInfo(info)
      } catch (error) {
        console.error('Failed to load user info:', error)
      }
    }
    loadUserInfo()
  }, [])

  // Check if we have any active batch jobs on mount
  useEffect(() => {
    const batchJobs = activeJobs.filter(job => 
      job.filename.toLowerCase().endsWith('.csv') || 
      job.filename.toLowerCase().endsWith('.xlsx')
    )
    if (batchJobs.length > 0 && !currentJobId) {
      // Resume the most recent job
      const latestJob = batchJobs.sort((a, b) => 
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      )[0]
      setCurrentJobId(latestJob.jobId)
    }
  }, [activeJobs, currentJobId])

  // Handle pending batch file from scrub page
  useEffect(() => {
    let isProcessing = false // Flag to prevent duplicate processing
    
    const loadPendingFile = async () => {
      if (pendingBatchFile && pendingBatchFile.scrubbed && !isProcessing) {
        isProcessing = true // Set flag immediately to prevent re-entry
        
        try {
          console.log('Loading pending batch file:', pendingBatchFile.filename)
          
          // Clear pending file IMMEDIATELY to prevent re-triggering
          const fileToProcess = { ...pendingBatchFile }
          setPendingBatchFile(null)
          
          // Determine the correct API endpoint based on source
          const downloadUrl = fileToProcess.isS3 
            ? `${PROPERTY_API_URL}/s3-scrub/download/${fileToProcess.filename}`
            : `${API_BASE_URL}/scrubbed-download/${fileToProcess.filename}`
          
          console.log('Fetching file from:', downloadUrl)
          
          // Fetch the scrubbed file
          const response = await fetch(downloadUrl, {
            headers: { 'x-api-key': API_KEY }
          })

          if (!response.ok) {
            const errorText = await response.text()
            console.error('Download failed:', response.status, errorText)
            throw new Error(`Failed to load scrubbed file: ${response.status}`)
          }

          const blob = await response.blob()
          const file = new File([blob], fileToProcess.filename, { type: blob.type })
          
          // Set the file
          setFile(file)

          // Parse headers
          const reader = new FileReader()
          reader.onload = (e) => {
            const data = new Uint8Array(e.target?.result as ArrayBuffer)
            const workbook = XLSX.read(data, { type: 'array' })
            const sheet = workbook.Sheets[workbook.SheetNames[0]]
            const json = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as string[][]
            const headers = json[0]
            setFileHeaders(headers)
            
            const initialMapping: ColumnMapping = { latitude: '', longitude: '' }
            expectedColumns.forEach((col) => {
              const match = headers.find((h) => h.toLowerCase() === col.toLowerCase())
              if (match) initialMapping[col as keyof ColumnMapping] = match
            })
            setColumnMapping(initialMapping)
            setIsUploaded(true)

            // Auto-start analysis if requested (only once)
            if (fileToProcess.autoStart && !currentJobId) {
              console.log('Auto-starting analysis for:', fileToProcess.filename)
              // Small delay to ensure state is set
              setTimeout(() => {
                handleUploadForScrubbedFile(file, initialMapping)
              }, 500)
            }
          }
          reader.readAsArrayBuffer(file)
        } catch (error: any) {
          console.error('Failed to load pending file:', error)
          setError(error.message || 'Failed to load scrubbed file')
          // Clear the pending file on error too
          setPendingBatchFile(null)
        } finally {
          isProcessing = false
        }
      }
    }

    loadPendingFile()
  }, [pendingBatchFile])

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    // Reset all state immediately
    setFile(selectedFile)
    setFileHeaders([])
    setResults([])
    setIsUploaded(false)
    setError('')
    setCurrentJobId(null)
    
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer)
        const workbook = XLSX.read(data, { type: 'array' })
        const sheet = workbook.Sheets[workbook.SheetNames[0]]
        const json = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as string[][]
        const headers = json[0]
        
        if (!headers || headers.length === 0) {
          setError('Invalid file: No headers found')
          return
        }
        
        setFileHeaders(headers)
        
        const initialMapping: ColumnMapping = { latitude: '', longitude: '' }
        expectedColumns.forEach((col) => {
          const match = headers.find((h) => h.toLowerCase() === col.toLowerCase())
          if (match) initialMapping[col as keyof ColumnMapping] = match
        })
        setColumnMapping(initialMapping)
        setIsUploaded(true)
      } catch (error: any) {
        console.error('File parsing error:', error)
        setError(`Failed to parse file: ${error.message}`)
      }
    }
    reader.onerror = () => {
      setError('Failed to read file')
    }
    reader.readAsArrayBuffer(selectedFile)
  }

  const handleColumnMappingChange = (expected: string, selected: string) => {
    setColumnMapping({ ...columnMapping, [expected]: selected })
  }

  const handleUploadForScrubbedFile = async (fileToUpload: File, mapping: ColumnMapping) => {
    try {
      setError('')
      const formData = new FormData()
      formData.append('file', fileToUpload)
      
      // Add column mapping if specified
      if (mapping.latitude && mapping.longitude) {
        const columnMap = {
          PropertyLatitude: mapping.latitude,
          PropertyLongitude: mapping.longitude
        }
        formData.append('column_mapping', JSON.stringify(columnMap))
      }
      
      // Add user info
      formData.append('user', userInfo?.username || userInfo?.userId || 'unknown')
      if (userInfo?.email) {
        formData.append('email', userInfo.email)
      }

      console.log('Submitting batch analysis job for:', fileToUpload.name)
      
      // Submit job using the batch upload API
      const response = await fetch(`${API_BASE_URL}/analyze/batch`, {
        method: 'POST',
        headers: {
          'x-api-key': API_KEY,
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const data = await response.json()
      const jobId = data.job?.job_id || data.job_id
      
      // Count rows in file for display
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result as string
        const lines = text.split('\n').filter(line => line.trim())
        const totalRows = Math.max(0, lines.length - 1) // Subtract header row
        
        // Add job to context
        addJob({
          jobId: jobId,
          status: 'queued',
          totalRows: totalRows,
          completedRows: 0,
          filename: fileToUpload.name,
          createdAt: new Date().toISOString(),
        })
        
        setCurrentJobId(jobId)
      }
      reader.readAsText(fileToUpload)
    } catch (error: any) {
      console.error('Upload failed:', error)
      const errorDetail = error.message || 'Upload failed. Please try again.'
      setError(formatErrorMessage(errorDetail))
    }
  }

  const handleUpload = async () => {
    if (!file) return
    await handleUploadForScrubbedFile(file, columnMapping)
  }

  const handleDownload = async (jobId: string) => {
    try {
      setError('')
      
      const response = await api.get(`/batch/download/${jobId}`, {
        responseType: 'blob',
      })
      
      const blob = response.data
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `analysis-results-${jobId}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Download failed:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to download results'
      setError(formatErrorMessage(errorMessage))
    }
  }

  const handleRemoveJob = (jobId: string) => { //! urm,what the.. sigma
    removeJob(jobId)
    if (currentJobId === jobId) {
      setCurrentJobId(null)
    }
  }

  const handleCancelJob = async (jobId: string) => {
    try {
      setError('')
      
      // const response = await api.delete(`/api/jobs/${jobId}`, {
      //   headers: {
      //     'x-user-id': userInfo?.userId || 'unknown',
      //   },
      // })
      const response = fetch(`${API_BASE_URL}/batch/cancel/${jobId}`)
      
      // Update job status to cancelled
      const job = getJob(jobId)
      if (job) {
        job.status = 'cancelled'
      }
      console.log(`Job ${jobId} cancelled successfully`)
    } catch (error: any) {
      console.error('Cancel failed:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to cancel job'
      setError(formatErrorMessage(errorMessage))
    }
  }

  // Get batch-related jobs
  const batchJobs = activeJobs.filter(job => 
    job.filename.toLowerCase().endsWith('.csv') || 
    job.filename.toLowerCase().endsWith('.xlsx')
  ).sort((a, b) => 
    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  )

  return (
    <div className="space-y-6">
      {/* Upload Card */}
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <FileSpreadsheet className="h-6 w-6 text-primary" />
            Upload Batch File
          </CardTitle>
          <CardDescription>
            Upload a CSV or Excel file containing latitude and longitude coordinates for bulk property analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Upload Section */}
          <div className="space-y-3">
            <label className="block">
              <div className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-all duration-200 hover:border-primary hover:bg-accent
                ${file ? 'border-primary bg-accent' : 'border-border'}
              `}>
                <input
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="flex flex-col items-center gap-3">
                  {file ? (
                    <>
                      <CheckCircle2 className="h-12 w-12 text-primary" />
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-foreground">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(file.size / 1024).toFixed(2)} KB • Ready to process
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <Upload className="h-12 w-12 text-muted-foreground" />
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-foreground">
                          Click to upload or drag and drop
                        </p>
                        <p className="text-xs text-muted-foreground">
                          CSV or XLSX files (max 50MB)
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </label>
          </div>

          {/* Column Mapping Section */}
          {isUploaded && fileHeaders.length > 0 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-foreground">Column Mapping</h3>
                <p className="text-sm text-muted-foreground">
                  Map your spreadsheet columns to the required fields
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {expectedColumns.map((col) => (
                  <div key={col} className="space-y-2">
                    <label className="text-sm font-medium text-foreground capitalize">
                      {col}
                    </label>
                    <select
                      value={columnMapping[col as keyof ColumnMapping] || ''}
                      onChange={(e) => handleColumnMappingChange(col, e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="">Select column...</option>
                      {fileHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {/* Start Analysis Button */}
              <div className="flex items-center gap-3 pt-4">
                <Button
                  onClick={handleUpload}
                  disabled={!file}
                  className="px-6 py-2 text-base"
                  size="lg"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Analysis
                </Button>
                <p className="text-sm text-muted-foreground">
                  Column mapping is optional - will auto-detect if not specified
                </p>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-destructive">Error</p>
                <p className="text-sm text-destructive/90 mt-1">{error}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Jobs Card */}
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center justify-between">
            <span>Active Jobs</span>
            <span className="text-base font-normal text-muted-foreground">
              {batchJobs.length} {batchJobs.length === 1 ? 'job' : 'jobs'}
            </span>
          </CardTitle>
          <CardDescription>
            Monitor the progress of your batch analysis jobs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {batchJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileSpreadsheet className="h-16 w-16 text-muted-foreground/40 mb-4" />
              <p className="text-lg font-medium text-muted-foreground">No active jobs</p>
              <p className="text-sm text-muted-foreground mt-1">
                Upload a file to start batch analysis
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {batchJobs.map((job) => (
                <JobMonitor
                  key={job.jobId}
                  jobId={job.jobId}
                  onDownload={handleDownload}
                  onRemove={handleRemoveJob}
                  onCancel={handleCancelJob}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
