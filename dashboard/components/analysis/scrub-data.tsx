"use client"

import React, { useState, useEffect } from 'react'
import { Upload, FileSpreadsheet, AlertCircle, Loader2, Play, Download, CheckCircle, RefreshCw, Cloud, FolderOpen, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { useAnalysis } from '@/contexts/analysis-context'

interface ScrubResult {
  message: string
  output_files?: string[]
  total_rows?: number
}

interface ScrubbledFile {
  name: string
  jobId?: string
  status?: 'idle' | 'analyzing' | 'analyzed' | 'committing' | 'committed' | 'failed' | 'sent-to-batch' | 'preparing-batch'
  error?: string
  sentToBatch?: boolean
  sentAt?: string
}

interface S3File {
  key: string
  name: string
  relative_path: string
  size: number
  last_modified: string
}



export function ScrubData() {
  const { addJob, setPendingBatchFile, navigateToSection } = useAnalysis()
  const [file, setFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [error, setError] = useState<string>('')
  const [successMessage, setSuccessMessage] = useState<string>('')
  const [scrubbledFiles, setScrubbledFiles] = useState<ScrubbledFile[]>([])
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  
  // S3 State
  const [s3Files, setS3Files] = useState<S3File[]>([])
  const [s3Directories, setS3Directories] = useState<string[]>([])
  const [selectedS3Directory, setSelectedS3Directory] = useState<string | null>(null)
  const [isLoadingS3, setIsLoadingS3] = useState(false)
  const [s3Error, setS3Error] = useState<string>('')

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const PROPERTY_API_URL = process.env.NEXT_PUBLIC_PROPERTY_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  // Load S3 files on mount
  useEffect(() => {
    fetchS3Directories()
  }, [])

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    if (!selectedFile.name.toLowerCase().endsWith('.csv') && !selectedFile.name.toLowerCase().endsWith('.xlsx')) {
      setError('Please select a CSV or XLSX file')
      return
    }

    setFile(selectedFile)
    setError('')
  }

  // S3 Functions
  const fetchS3Directories = async () => {
    try {
      const response = await fetch(`${PROPERTY_API_URL}/s3-scrub/directories`, {
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Failed to fetch S3 directories')

      const data = await response.json()
      setS3Directories(data.directories || [])
    } catch (error: any) {
      console.error('Failed to fetch S3 directories:', error)
      setS3Error(error.message)
    }
  }

  const fetchS3Files = async (directory?: string | null) => {
    setIsLoadingS3(true)
    setS3Error('')
    try {
      const url = directory 
        ? `${PROPERTY_API_URL}/s3-scrub/files?directory=${encodeURIComponent(directory)}`
        : `${PROPERTY_API_URL}/s3-scrub/files`
      
      const response = await fetch(url, {
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Failed to fetch S3 files')

      const data = await response.json()
      setS3Files(data.files || [])
    } catch (error: any) {
      console.error('Failed to fetch S3 files:', error)
      setS3Error(error.message)
    } finally {
      setIsLoadingS3(false)
    }
  }

  const downloadS3File = async (filePath: string, fileName: string) => {
    try {
      const response = await fetch(`${PROPERTY_API_URL}/s3-scrub/download/${encodeURIComponent(filePath)}`, {
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: any) {
      alert(`Failed to download: ${error.message}`)
    }
  }

  const deleteS3File = async (filePath: string) => {
    if (!confirm(`Are you sure you want to delete ${filePath}?`)) return

    try {
      const response = await fetch(`${PROPERTY_API_URL}/s3-scrub/files/${encodeURIComponent(filePath)}`, {
        method: 'DELETE',
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Delete failed')

      // Refresh the file list
      await fetchS3Files(selectedS3Directory)
      setSuccessMessage(`File "${filePath}" deleted successfully`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (error: any) {
      alert(`Failed to delete: ${error.message}`)
    }
  }

  const deleteS3Directory = async (directory: string) => {
    if (!confirm(`Are you sure you want to delete all files in "${directory}"?`)) return

    try {
      const response = await fetch(`${PROPERTY_API_URL}/s3-scrub/directories/${encodeURIComponent(directory)}`, {
        method: 'DELETE',
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Delete failed')

      // Refresh directories and clear selection
      await fetchS3Directories()
      if (selectedS3Directory === directory) {
        setSelectedS3Directory(null)
        setS3Files([])
      }
      setSuccessMessage(`Directory "${directory}" deleted successfully`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (error: any) {
      alert(`Failed to delete directory: ${error.message}`)
    }
  }

  const sendS3FileToBatch = async (file: S3File) => {
    setSuccessMessage(`File "${file.name}" sent to Batch Analysis`)
    setTimeout(() => setSuccessMessage(''), 5000)

    // Set pending file info in context
    setPendingBatchFile({
      filename: file.relative_path,
      scrubbed: true,
      autoStart: false,
      isS3: true  // Flag to indicate this is from S3
    })

    // Navigate to batch analysis page
    setTimeout(() => {
      if (navigateToSection) {
        navigateToSection('batch-analysis')
      }
    }, 100)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleUploadToS3 = async () => {
    if (!file) return

    setIsProcessing(true)
    setUploadProgress(0)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Use XMLHttpRequest for progress tracking
      const xhr = new XMLHttpRequest()
      
      const uploadPromise = new Promise<any>((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100)
            setUploadProgress(percentComplete)
          }
        })

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText)
              resolve(response)
            } catch (e) {
              reject(new Error('Invalid response from server'))
            }
          } else {
            try {
              const errorData = JSON.parse(xhr.responseText)
              reject(new Error(errorData.detail || `Upload failed with status ${xhr.status}`))
            } catch (e) {
              reject(new Error(`Upload failed with status ${xhr.status}`))
            }
          }
        })

        xhr.addEventListener('error', () => {
          reject(new Error('Network error during upload'))
        })

        xhr.addEventListener('abort', () => {
          reject(new Error('Upload was cancelled'))
        })

        xhr.open('POST', `${PROPERTY_API_URL}/s3-scrub/upload`)
        xhr.setRequestHeader('x-api-key', API_KEY)
        xhr.send(formData)
      })

      const data = await uploadPromise
      
      // Refresh S3 files list
      await fetchS3Directories()
      await fetchS3Files(selectedS3Directory)
      setFile(null)
      setUploadProgress(100)
      setSuccessMessage(`File uploaded successfully to S3: ${data.key}`)
      setTimeout(() => {
        setSuccessMessage('')
        setUploadProgress(0)
      }, 5000)
    } catch (error: any) {
      console.error('Upload failed:', error)
      setError(error.message || 'Upload failed. Please try again.')
      setUploadProgress(0)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleScrub = async () => {
    if (!file) return

    setIsProcessing(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE_URL}/scrub`, {
        method: 'POST',
        headers: { 'x-api-key': API_KEY },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Scrub failed')
      }

      const data: ScrubResult = await response.json()
      
      // Refresh scrubbed files list
      // await fetchScrubbledFiles()
      // setSuccessMessage('Data scrubbed successfully!')
      setTimeout(() => setSuccessMessage(''), 5000)
    } catch (error: any) {
      console.error('Scrub failed:', error)
      setError(error.message || 'Scrub failed. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const downloadFile = async (filename: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/scrubbed-download/${filename}`, {
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: any) {
      alert(`Failed to download: ${error.message}`)
    }
  }

  const runAnalysis = async (filename: string, index: number) => {
    // Check if already processing this file to prevent duplicate submissions
    if (scrubbledFiles[index].status === 'sent-to-batch' || scrubbledFiles[index].status === 'preparing-batch') {
      console.log('File already sent to batch, ignoring duplicate click')
      return
    }

    // Immediately show preparing status for instant feedback
    setScrubbledFiles(prevFiles => {
      const preparingFiles = [...prevFiles]
      preparingFiles[index].status = 'preparing-batch'
      return preparingFiles
    })

    // After a brief moment, mark as sent to batch
    setTimeout(() => {
      setScrubbledFiles(prevFiles => {
        const updatedFiles = [...prevFiles]
        updatedFiles[index].status = 'sent-to-batch'
        updatedFiles[index].sentToBatch = true
        updatedFiles[index].sentAt = new Date().toISOString()
        return updatedFiles
      })
    }, 100)

    // Show success message
    setSuccessMessage(`File "${filename}" sent to Batch Analysis`)
    setTimeout(() => setSuccessMessage(''), 5000) // Clear after 5 seconds

    // Set pending file info in context (without autoStart)
    setPendingBatchFile({
      filename: filename,
      scrubbed: true,
      autoStart: false  // Don't auto-submit, just pre-fill the file
    })

    // Navigate to batch analysis page
    setTimeout(() => {
      if (navigateToSection) {
        navigateToSection('batch-analysis')
      } else {
        console.error('Navigation function not available')
      }
    }, 100)
  }

  const pollAnalysisStatus = async (jobId: string, index: number) => {
    const maxAttempts = 60
    let attempts = 0

    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/analysis/status/${jobId}`, {
          headers: { 'x-api-key': API_KEY }
        })

        if (!response.ok) throw new Error('Status check failed')

        const data = await response.json()

        if (data.status === 'completed') {
          setScrubbledFiles(prevFiles => {
            const updatedFiles = [...prevFiles]
            updatedFiles[index].status = 'analyzed'
            updatedFiles[index].jobId = jobId
            return updatedFiles
          })
          return
        } else if (data.status === 'failed') {
          setScrubbledFiles(prevFiles => {
            const updatedFiles = [...prevFiles]
            updatedFiles[index].status = 'failed'
            updatedFiles[index].error = data.error || 'Analysis failed'
            return updatedFiles
          })
          return
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 2000)
        } else {
          throw new Error('Analysis timeout')
        }
      } catch (error: any) {
        setScrubbledFiles(prevFiles => {
          const updatedFiles = [...prevFiles]
          updatedFiles[index].status = 'failed'
          updatedFiles[index].error = error.message
          return updatedFiles
        })
      }
    }

    checkStatus()
  }

  const downloadAnalysis = async (jobId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/analysis/review/${jobId}`, {
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analyzed_${jobId}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: any) {
      alert(`Failed to download analysis: ${error.message}`)
    }
  }

  const commitToDynamo = async (jobId: string, index: number) => {
    setScrubbledFiles(prevFiles => {
      const updatedFiles = [...prevFiles]
      updatedFiles[index].status = 'committing'
      return updatedFiles
    })

    try {
      const response = await fetch(`${API_BASE_URL}/analysis/commit/${jobId}`, {
        method: 'POST',
        headers: { 'x-api-key': API_KEY }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Commit failed')
      }

      // Poll for commit completion
      pollCommitStatus(jobId, index)
    } catch (error: any) {
      console.error('Commit failed:', error)
      setScrubbledFiles(prevFiles => {
        const updatedFiles = [...prevFiles]
        updatedFiles[index].status = 'failed'
        updatedFiles[index].error = error.message
        return updatedFiles
      })
    }
  }

  const pollCommitStatus = async (jobId: string, index: number) => {
    const maxAttempts = 30
    let attempts = 0

    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/analysis/status/${jobId}`, {
          headers: { 'x-api-key': API_KEY }
        })

        if (!response.ok) throw new Error('Status check failed')

        const data = await response.json()

        if (data.committed) {
          setScrubbledFiles(prevFiles => {
            const updatedFiles = [...prevFiles]
            updatedFiles[index].status = 'committed'
            return updatedFiles
          })
          return
        } else if (data.status === 'commit_failed') {
          setScrubbledFiles(prevFiles => {
            const updatedFiles = [...prevFiles]
            updatedFiles[index].status = 'failed'
            updatedFiles[index].error = data.error || 'Commit failed'
            return updatedFiles
          })
          return
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 2000)
        }
      } catch (error: any) {
        setScrubbledFiles(prevFiles => {
          const updatedFiles = [...prevFiles]
          updatedFiles[index].status = 'failed'
          updatedFiles[index].error = error.message
          return updatedFiles
        })
      }
    }

    checkStatus()
  }

  return (
    <div className="space-y-6">
      {/* File Upload to S3 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload File to S3
          </CardTitle>
          <CardDescription>
            Select a CSV or XLSX file to upload to S3 for processing
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={handleFileChange}
                disabled={isProcessing}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <Button
                onClick={handleUploadToS3}
                disabled={!file || isProcessing}
                className="flex items-center gap-2 whitespace-nowrap"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Cloud className="w-4 h-4" />
                )}
                {isProcessing ? `Uploading... ${uploadProgress}%` : 'Upload to S3'}
              </Button>
            </div>

            {file && !isProcessing && (
              <div className="text-sm text-muted-foreground">
                Selected: {file.name} ({formatFileSize(file.size)})
              </div>
            )}

            {/* Upload Progress Bar */}
            {isProcessing && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Uploading {file?.name}...</span>
                  <span className="font-medium">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2.5">
                  <div 
                    className="bg-primary h-2.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                {uploadProgress === 100 && (
                  <div className="text-sm text-muted-foreground">
                    Finalizing upload...
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            {successMessage && (
              <div className="flex items-center gap-2 text-sm text-primary p-2 bg-primary/10 rounded-md border border-primary/20">
                <CheckCircle className="w-4 h-4" />
                {successMessage}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* S3 Scrubbed Files Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Cloud className="w-5 h-5" />
                S3 Scrubbed Files
              </CardTitle>
              <CardDescription>
                Browse and download scrubbed CSV files from S3 bucket
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  fetchS3Directories()
                  if (selectedS3Directory) {
                    fetchS3Files(selectedS3Directory)
                  }
                }}
                disabled={isLoadingS3}
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingS3 ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {s3Error && (
            <div className="flex items-center gap-2 text-destructive mb-4">
              <AlertCircle className="w-4 h-4" />
              {s3Error}
            </div>
          )}

          {/* Directory Selection */}
          <div className="mb-4">
            <label className="text-sm font-medium mb-2 block">Select Date Directory</label>
            <div className="flex flex-wrap gap-2">
              <Button
                variant={selectedS3Directory === null ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setSelectedS3Directory(null)
                  fetchS3Files(null)
                }}
              >
                <FolderOpen className="w-4 h-4 mr-1" />
                All Files
              </Button>
              {s3Directories.map((dir) => (
                <div key={dir} className="flex items-center gap-1">
                  <Button
                    variant={selectedS3Directory === dir ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setSelectedS3Directory(dir)
                      fetchS3Files(dir)
                    }}
                  >
                    <FolderOpen className="w-4 h-4 mr-1" />
                    {dir}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                    onClick={() => deleteS3Directory(dir)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* S3 Files List */}
          <div className="space-y-2">
            {isLoadingS3 ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : s3Files.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {selectedS3Directory 
                  ? `No files found in "${selectedS3Directory}"`
                  : "Select a directory or click 'All Files' to browse S3 files"
                }
              </div>
            ) : (
              <>
                <div className="text-sm text-muted-foreground mb-2">
                  {s3Files.length} file(s) found
                </div>
                <div className="border rounded-md divide-y">
                  {s3Files.map((file) => (
                    <div 
                      key={file.key} 
                      className="flex items-center justify-between p-3 hover:bg-muted/50"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{file.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {file.relative_path} • {formatFileSize(file.size)} • {new Date(file.last_modified).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => downloadS3File(file.relative_path, file.name)}
                        >
                          <Download className="w-4 h-4 mr-1" />
                          Download
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => sendS3FileToBatch(file)}
                        >
                          <Play className="w-4 h-4 mr-1" />
                          Analyze
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => deleteS3File(file.relative_path)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}