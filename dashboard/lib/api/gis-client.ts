// GIS Module API Client

import type {
  ParcelAnalysis,
  BatchJob,
  BatchAnalysisResult,
  SystemHealth,
  AnalyticsData,
  LogEntry,
  Property,
  PropertySearchResult,
  PropertyCreate,
  PropertyUpdate,
  UserActivity,
  PropertyStatistics
} from '@/lib/types/gis'

const GIS_API_URL = process.env.NEXT_PUBLIC_GIS_API_URL || 'http://10.8.0.1:8001'
const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || ''

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>
}

class GISApiClient {
  private baseUrl: string
  private apiKey: string

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl
    this.apiKey = apiKey
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { params, ...fetchOptions } = options

    let url = `${this.baseUrl}${endpoint}`
    
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value))
      })
      url += `?${searchParams.toString()}`
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `API Error: ${response.status}`)
    }

    return response.json()
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; message: string }> {
    return this.request('/health')
  }

  // Single Parcel Analysis
  async analyzeParcel(gid: number): Promise<ParcelAnalysis> {
    return this.request(`/analyze/${gid}`)
  }

  // Rerun Analysis
  async rerunAnalysis(gid: number): Promise<ParcelAnalysis> {
    return this.request(`/analyze/rerun/${gid}`, { method: 'POST' })
  }

  // Road Frontage
  async getRoadFrontage(gid: number) {
    return this.request(`/analysis/road-frontage/${gid}`)
  }

  // Electric Lines
  async getElectricLines(gid: number) {
    return this.request(`/analysis/electric-lines/${gid}`)
  }

  // Gas Pipelines
  async getGasPipelines(gid: number) {
    return this.request(`/analysis/gas-pipelines/${gid}`)
  }

  // Water Wells
  async getWaterWells(gid: number) {
    return this.request(`/analysis/water-wells/${gid}`)
  }

  // Buildable Area
  async getBuildableArea(gid: number) {
    return this.request(`/analysis/buildable-area/${gid}`)
  }

  // Elevation Change
  async getElevationChange(gid: number) {
    return this.request(`/analysis/elevation-change/${gid}`)
  }

  // Slope
  async getSlope(gid: number) {
    return this.request(`/analysis/slope/${gid}`)
  }

  // Tree Coverage
  async getTreeCoverage(gid: number) {
    return this.request(`/analysis/tree-coverrage/${gid}`)
  }

  // Images
  async getParcelImage(gid: number, options?: {
    buffer_percent?: number
    boundary_color?: string
    boundary_thickness?: number
  }) {
    return this.request(`/analysis/image/parcel/${gid}`, { params: options as any })
  }

  async getTreeCoverageImage(gid: number) {
    return this.request(`/analysis/image/tree_coverage/${gid}`)
  }

  async getRoadFrontageImage(gid: number) {
    return this.request(`/analysis/image/road_frontage/${gid}`)
  }

  async getContourImage(gid: number) {
    return this.request(`/analysis/image/contour/${gid}`)
  }

  async getWaterFeaturesImage(gid: number) {
    return this.request(`/analysis/image/water_features/${gid}`)
  }

  async getFloodHazardImage(gid: number) {
    return this.request(`/analysis/image/flood_hazard/${gid}`)
  }

  // Batch Analysis
  async uploadBatchFile(file: File, columnMapping?: Record<string, string>): Promise<{ job_id: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    if (columnMapping) {
      formData.append('column_mapping', JSON.stringify(columnMapping))
    }

    const response = await fetch(`${this.baseUrl}/v1/analysis/batch-upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
      },
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`)
    }

    return response.json()
  }

  async getBatchJobStatus(jobId: string): Promise<BatchJob> {
    return this.request(`/v1/analysis/job-status/${jobId}`)
  }

  async getBatchJobResult(jobId: string, flattened = false): Promise<{
    job_id: string
    status: string
    results: BatchAnalysisResult[]
    total_count: number
  }> {
    return this.request(`/v1/analysis/job-result/${jobId}`, { params: { flattened } })
  }
  async downloadBatchResultCSV(jobId: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/v1/analysis/job-result-csv/${jobId}`, {
      headers: {
        'X-API-Key': this.apiKey,
      },
    })

    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`)
    }

    return response.blob()
  }

  async getBatchDuration(batchId: string, strict = false): Promise<{
    batch_id: string
    duration_mm_ss: string
  }> {
    return this.request(`/analysis/batch-time/${batchId}`, { params: { strict } })
  }

  async getBatchWindow(batchId: string, strict = false): Promise<{
    batch_id: string
    start_time_iso: string
    end_time_iso: string
    duration_mm_ss: string
  }> {
    return this.request(`/analysis/batch-window/${batchId}`, { params: { strict } })
  }

  // Logs
  async listLogs(): Promise<{ logs: string[] }> {
    return this.request('/logs/list')
  }

  async getLogs(name: string, lines = 200, offset = 0): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/logs?name=${name}&lines=${lines}&offset=${offset}`,
      {
        headers: {
          'X-API-Key': this.apiKey,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to fetch logs: ${response.status}`)
    }

    return response.text()
  }

  async searchProperties(params: {
    status?: string
    user_name?: string
    seller_name?: string
    owner_name?: string
    min_price?: number
    max_price?: number
    min_acres?: number
    max_acres?: number
    county?: string
    limit?: number
    offset?: number
  }): Promise<PropertySearchResult> {
    return this.request('/catalogue/search', { params })
  }

  async listProperties(params?: {
    limit?: number
    offset?: number
    order_by?: string
    desc?: boolean
  }): Promise<PropertySearchResult> {
    return this.request('/catalogue/properties', { params })
  }

  // CHANGED: docId -> propertyId to match backend
  async getProperty(propertyId: string): Promise<Property> {
    return this.request(`/catalogue/properties/${propertyId}`)
  }

  async createProperty(property: PropertyCreate): Promise<{ property_id: string; message: string }> {
    return this.request('/catalogue/properties', {
      method: 'POST',
      body: JSON.stringify(property),
    })
  }

  async updateProperty(propertyId: string, property: PropertyUpdate): Promise<Property> {
    return this.request(`/catalogue/properties/${propertyId}`, {
      method: 'PUT',
      body: JSON.stringify(property),
    })
  }

  async deleteProperty(propertyId: string): Promise<{ message: string }> {
    return this.request(`/catalogue/properties/${propertyId}`, {
      method: 'DELETE',
    })
  }

  async getUserProperties(userName: string, limit = 100): Promise<Property[]> {
    return this.request(`/catalogue/users/${userName}/properties`, {
      params: { limit },
    })
  }

  async getUserActivity(userName: string): Promise<UserActivity> {
    return this.request(`/catalogue/users/${userName}/activity`)
  }

  async getPropertyStatistics(): Promise<PropertyStatistics> {
    return this.request('/catalogue/statistics')
  }
}

// Export singleton instance
export const gisApi = new GISApiClient(GIS_API_URL, API_KEY)

// Export class for custom instances
export default GISApiClient
