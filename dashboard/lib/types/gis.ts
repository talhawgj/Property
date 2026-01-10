// GIS Module Types

export interface ParcelAnalysis {
  gid: number
  property_id?: string
  latitude: number
  longitude: number
  road_frontage?: RoadFrontageData
  electric_lines?: ElectricLinesData
  gas_pipelines?: GasPipelinesData
  water_wells?: WaterWellsData
  buildable_area?: BuildableAreaData
  elevation_change?: ElevationChangeData
  slope?: SlopeData
  tree_coverage?: TreeCoverageData
  water_features?: WaterFeaturesData
  flood_hazard?: FloodHazardData
  created_at?: string
  updated_at?: string
}

export interface RoadFrontageData {
  has_road_access: boolean
  frontage_length_feet: number
  nearest_road_distance_feet: number
  road_names: string[]
}

export interface ElectricLinesData {
  has_electric_access: boolean
  nearest_line_distance_feet: number
  line_count: number
}

export interface GasPipelinesData {
  has_gas_access: boolean
  nearest_pipeline_distance_feet: number
  pipeline_count: number
}

export interface WaterWellsData {
  wells_on_property: number
  wells_within_1000ft: number
  nearest_well_distance_feet: number
}

export interface BuildableAreaData {
  total_area_acres: number
  buildable_area_acres: number
  buildable_percentage: number
  constraints: string[]
}

export interface ElevationChangeData {
  min_elevation_feet: number
  max_elevation_feet: number
  elevation_change_feet: number
  average_elevation_feet: number
}

export interface SlopeData {
  average_slope_percent: number
  max_slope_percent: number
  steep_areas_percentage: number
  slope_category: 'flat' | 'gentle' | 'moderate' | 'steep' | 'very_steep'
}

export interface TreeCoverageData {
  coverage_percentage: number
  tree_count_estimate: number
  dominant_species: string[]
}

export interface WaterFeaturesData {
  has_water_features: boolean
  feature_types: string[]
  total_water_area_acres: number
  nearest_water_distance_feet: number
}

export interface FloodHazardData {
  flood_zone: string
  flood_risk_level: 'minimal' | 'moderate' | 'high'
  in_100yr_floodplain: boolean
  in_500yr_floodplain: boolean
}

export interface BatchJob {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  error?: string
  total_count?: number
  processed_count?: number
  original_filename?: string
}

export interface BatchAnalysisResult {
  prop_id: string
  PropertyLatitude: number
  PropertyLongitude: number
  gid: number
  [key: string]: any
}

export interface SystemHealth {
  status: 'ok' | 'degraded' | 'down'
  uptime: string
  database_status: 'connected' | 'disconnected'
  redis_status: 'connected' | 'disconnected'
  s3_status: 'connected' | 'disconnected'
  active_jobs: number
  queue_length: number
}

export interface AnalyticsData {
  total_analyses: number
  analyses_today: number
  analyses_this_week: number
  analyses_this_month: number
  average_processing_time_seconds: number
  success_rate: number
  failed_analyses: number
  popular_features: {
    feature: string
    usage_count: number
  }[]
}

export interface User {
  id: string
  email: string
  api_key: string
  role: 'admin' | 'user' | 'viewer'
  created_at: string
  last_login?: string
  usage_count: number
  quota_limit?: number
  is_active: boolean
}

export interface LogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  gid?: number
  job_id?: string
  user_id?: string
}

// Property Catalogue Types
export interface PropertyImages {
  aerial?: string | null
  contour?: string | null
  flood?: string | null
  road_frontage?: string | null
  tree?: string | null
}

export interface PropertyAnalysis {
  buildable_area?: number | BuildableAreaData | null
  flood_hazard?: string | FloodHazardData | null
  electric_lines?: string | ElectricLinesData | null
  gas_lines?: string | GasPipelinesData | null
  road_analysis?: string | any | null
  well_analysis?: string | WaterWellsData | null
  wetland_analysis?: string | any | null
  lake_analysis?: string | any | null
  pond_analysis?: string | any | null
  stream_intersection?: string | any | null
  shoreline_analysis?: string | any | null
  tree_coverage?: number | TreeCoverageData | null
  elevation_change?: number | ElevationChangeData | null
  meta?: Meta | null
}
interface Meta{
  batch_id: string
  processing_mode: string
  execution_time_seconds: number
}
export interface Property {
  property_id: string
  gid?: number
  prop_id?: string
  owner_name?: string
  county?: string
  city?: string
  longitude?: number
  latitude?: number
  price_per_acre?: number | null
  situs_addr?: string
  acreage?: number
  status?: 'active' | 'inactive' | 'activelisting'
  user_name?: string | null
  seller_name?: string | null
  sell_price?: number | null
  batch_id?: string
  images?: PropertyImages
  analysis?: PropertyAnalysis | any
  source_data?: Record<string, any>
  created_at?: any
  updated_at?: any
}

export interface PropertyCreate {
  gid?: number
  prop_id?: string
  county?: string
  owner_name?: string
  situs_addr?: string
  acreage?: number
  status?: 'active' | 'inactive'
  user_name?: string
  seller_name?: string
  sell_price?: number
  description?: string
  images?: string[]
  processing_mode?: string
  batch_id?: string
}

export interface PropertyUpdate {
  gid?: number
  prop_id?: string | null
  county?: string
  city?: string
  state?: string
  zip?: number
  latitude?: number
  longitude?: number
  property_type?: string
  owner_name?: string
  situs_addr?: string
  acreage?: number
  lot_size?: number
  beds?: number
  baths?: number
  built_in?: number
  status?: 'active' | 'inactive' | 'activelisting'
  user_name?: string | null
  seller_name?: string
  seller_email?: string
  seller_phone?: string
  seller_office?: string
  sell_price?: number
  price_per_acre?: number | null
  days_on_market?: number
  description?: string | null
  images?: PropertyImages
  analysis?: PropertyAnalysis
  source_data?: Record<string, any>
  analysis_duration?: number
  processing_mode?: string
  is_batch?: boolean
  batch_id?: string
}

export interface PropertySearchResult {
  properties: Property[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface UserActivity {
  user_name: string
  total_properties: number
  active_properties: number
  inactive_properties: number
  total_acres: number
  total_value: number
  recent_properties: Property[]
}

export interface PropertyStatistics {
  total_properties: number
  active_properties: number
  inactive_properties: number
  unique_users: number
  unique_counties: number
  total_acres: number
  average_price: number
}
