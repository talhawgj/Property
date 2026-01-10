/**
 * Example implementation for deleting a job
 * Add this to your batch-analysis component or job management component
 */

import api from '@/lib/api'

/**
 * Permanently delete a job from the system
 * This removes it from the database, cache, and queue
 * 
 * The x-user-id header is automatically added by the api client
 * from the authenticated user's session
 */
export async function deleteJob(jobId: string): Promise<void> {
  try {
    const response = await api.delete(`/api/jobs/${jobId}/permanent`)
    console.log('Job deleted:', response.data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('You do not have permission to delete this job')
    } else if (error.response?.status === 404) {
      throw new Error('Job not found')
    } else {
      throw new Error(error.response?.data?.detail || 'Failed to delete job')
    }
  }
}

/**
 * Cancel a job (stops it but keeps in database)
 */
export async function cancelJob(jobId: string): Promise<void> {
  try {
    const response = await api.delete(`/api/jobs/${jobId}`)
    console.log('Job cancelled:', response.data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('You do not have permission to cancel this job')
    } else if (error.response?.status === 404) {
      throw new Error('Job not found')
    } else {
      throw new Error(error.response?.data?.detail || 'Failed to cancel job')
    }
  }
}

/**
 * Example usage in a component:
 * 
 * const handleDeleteJob = async (jobId: string) => {
 *   if (!confirm('Are you sure you want to permanently delete this job?')) {
 *     return
 *   }
 *   
 *   try {
 *     await deleteJob(jobId)
 *     // Remove from UI state
 *     removeJob(jobId)
 *     toast.success('Job deleted successfully')
 *   } catch (error) {
 *     console.error('Failed to delete job:', error)
 *     toast.error(error.message)
 *   }
 * }
 */
