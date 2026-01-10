"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface JobState {
  jobId: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  totalRows: number
  completedRows: number
  filename: string
  createdAt: string
  error?: string
  results?: any[]
}

interface PendingBatchFile {
  filename: string
  scrubbed: boolean
  autoStart?: boolean
  isS3?: boolean  // Flag to indicate file is from S3
}

interface AnalysisContextType {
  activeTab: string
  setActiveTab: (tab: string) => void
  batchState: any
  setBatchState: (state: any) => void
  singleState: any
  setSingleState: (state: any) => void
  // Job tracking
  activeJobs: JobState[]
  addJob: (job: JobState) => void
  updateJob: (jobId: string, updates: Partial<JobState>) => void
  removeJob: (jobId: string) => void
  getJob: (jobId: string) => JobState | undefined
  clearCompletedJobs: () => void
  // File transfer for batch analysis
  pendingBatchFile: PendingBatchFile | null
  setPendingBatchFile: (file: PendingBatchFile | null) => void
  // Navigation
  navigateToSection?: (section: string) => void
  setNavigateToSection: (fn: (section: string) => void) => void
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined)

const STORAGE_KEY = 'analysis_active_jobs'

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTab] = useState("batch")
  const [batchState, setBatchState] = useState<any>(null)
  const [singleState, setSingleState] = useState<any>(null)
  const [activeJobs, setActiveJobs] = useState<JobState[]>([])
  const [pendingBatchFile, setPendingBatchFile] = useState<PendingBatchFile | null>(null)
  const [navigateToSection, setNavigateToSection] = useState<((section: string) => void) | undefined>(undefined)

  // Load active jobs from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const jobs = JSON.parse(stored) as JobState[]
        // Only restore jobs that are not completed/failed/cancelled
        const activeJobsList = jobs.filter(
          job => job.status === 'queued' || job.status === 'processing'
        )
        setActiveJobs(activeJobsList)
      }
    } catch (error) {
      console.error('Failed to load active jobs:', error)
    }
  }, [])

  // Save active jobs to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(activeJobs))
    } catch (error) {
      console.error('Failed to save active jobs:', error)
    }
  }, [activeJobs])

  const addJob = (job: JobState) => {
    setActiveJobs(prev => {
      // Avoid duplicates
      const existing = prev.find(j => j.jobId === job.jobId)
      if (existing) return prev
      return [...prev, job]
    })
  }

  const updateJob = (jobId: string, updates: Partial<JobState>) => {
    setActiveJobs(prev =>
      prev.map(job =>
        job.jobId === jobId ? { ...job, ...updates } : job
      )
    )
  }

  const removeJob = (jobId: string) => {
    setActiveJobs(prev => prev.filter(job => job.jobId !== jobId))
  }

  const getJob = (jobId: string) => {
    return activeJobs.find(job => job.jobId === jobId)
  }

  const clearCompletedJobs = () => {
    setActiveJobs(prev =>
      prev.filter(job =>
        job.status !== 'completed' &&
        job.status !== 'failed' &&
        job.status !== 'cancelled'
      )
    )
  }

  return (
    <AnalysisContext.Provider
      value={{
        activeTab,
        setActiveTab,
        batchState,
        setBatchState,
        singleState,
        setSingleState,
        activeJobs,
        addJob,
        updateJob,
        removeJob,
        getJob,
        clearCompletedJobs,
        pendingBatchFile,
        setPendingBatchFile,
        navigateToSection,
        setNavigateToSection,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysis() {
  const context = useContext(AnalysisContext)
  if (context === undefined) {
    throw new Error('useAnalysis must be used within an AnalysisProvider')
  }
  return context
}
