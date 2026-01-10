"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, MapPin, Plus, Edit, Trash2, Home, RefreshCw, ExternalLink, X } from "lucide-react"
import { gisApi } from "@/lib/api/gis-client"
import type { Property, PropertyCreate, PropertyUpdate, PropertyStatistics, BuildableAreaData } from "@/lib/types/gis"
import { buildPropertyUrl } from "@/lib/utils/propertyUrl"
import { AddPropertyModal } from "@/components/property/AddPropertyModal"
import { FormField, InfoField, SectionHeader } from "@/templates/FormField"
import { FORM_FIELDS } from "@/lib/utils/formUtils"

type QueryMode = "in-memory-current" | "in-memory-all" | "dynamodb"

// Helper functions to format complex analysis values
function formatBuildableArea(value: number | BuildableAreaData | null | undefined): string | number | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') return value
  if (typeof value === 'object') {
    const acres = value.buildable_area_acres ?? (value as any).buildable_acres
    const percentage = value.buildable_percentage
    return `${acres?.toFixed(2) ?? 'N/A'} ac (${percentage?.toFixed(1) ?? 'N/A'}%)`
  }
  return null
}

function formatFloodHazard(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const zone = value.flood_zone_summary || value.flood_zone || 'Unknown'
    const acres = value.total_flood_acres
    if (acres > 0) return `Zone ${zone} (${acres.toFixed(2)} ac)`
    return `Zone ${zone} - No Flood Risk`
  }
  return null
}

function formatElectricLines(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const count = value.count || 0
    return `Intersects: ${intersects} (${count} lines)`
  }
  return null
}

function formatGasLines(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const count = value.count || 0
    return `Intersects: ${intersects} (${count} pipelines)`
  }
  return null
}

function formatRoadAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const length = value.length_ft || 0
    return `Road Access: ${intersects}, Frontage: ${length.toFixed(0)} ft`
  }
  return null
}

function formatWellAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const count = value.count || value.wells_on_property || 0
    const intersects = value.intersects !== undefined ? (value.intersects ? 'Yes' : 'No') : 'Unknown'
    return `Wells on Property: ${count}, Intersects: ${intersects}`
  }
  return null
}

function formatWetlandAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const cleared = value.cleared_area_acres || 0
    const pct = value.cleared_percentage || 0
    return `Intersects: ${intersects}, Cleared: ${cleared.toFixed(2)} ac (${pct.toFixed(1)}%)`
  }
  return null
}

function formatLakeAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const area = value.lake_area_acres || 0
    const count = value.unique_lake_count || 0
    return `Lakes: ${count}, Area: ${area.toFixed(2)} ac, Intersects: ${intersects}`
  }
  return null
}

function formatPondAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const area = value.pond_area_acres || 0
    const count = value.unique_pond_count || 0
    return `Ponds: ${count}, Area: ${area.toFixed(2)} ac, Intersects: ${intersects}`
  }
  return null
}

function formatStreamIntersection(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const intersects = value.intersects ? 'Yes' : 'No'
    const length = value.stream_length_ft || 0
    return `Intersects: ${intersects}, Length: ${length.toFixed(0)} ft`
  }
  return null
}

function formatShorelineAnalysis(value: any): string | null {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const lake = value.lake_length_ft || 0
    const beach = value.beach_length_ft || 0
    const river = value.riverine_length_ft || 0
    const total = lake + beach + river
    if (total === 0) return 'No Shoreline'
    return `Lake: ${lake.toFixed(0)} ft, Beach: ${beach.toFixed(0)} ft, River: ${river.toFixed(0)} ft`
  }
  return null
}

function formatTreeCoverage(value: any): string | null {
  if (!value) return null
  if (typeof value === 'number') return `${value}%`
  if (typeof value === 'object') {
    const tree = value.tree_percentage || value.coverage_percentage || 0
    const brush = value.brush_percentage || 0
    if (brush > 0) return `Trees: ${tree.toFixed(1)}%, Brush: ${brush.toFixed(1)}%`
    return `${tree.toFixed(1)}%`
  }
  return null
}

function formatElevationChange(value: any): string | null {
  if (!value) return null
  if (typeof value === 'number') return `${value} ft`
  if (typeof value === 'object') {
    const change = value.elevation_change_feet || value.elevation_change || 0
    const min = value.min_elevation_feet
    const max = value.max_elevation_feet
    if (min !== undefined && max !== undefined) {
      return `${change.toFixed(0)} ft (${min.toFixed(0)}-${max.toFixed(0)} ft)`
    }
    return `${change.toFixed(0)} ft`
  }
  return null
}

// Dynamic Form Renderer
function DynamicForm({ 
  fields, 
  data, 
  onChange 
}: { 
  fields: any[]
  data: any
  onChange: (key: string, value: any) => void 
}) {
  // Helper to get nested value (e.g., "images.aerial")
  const getNestedValue = (obj: any, path: string) => {
    const keys = path.split('.')
    let value = obj
    for (const key of keys) {
      value = value?.[key]
    }
    return value ?? ''
  }

  // Helper to check if image field has error/failed status
  const isImageError = (value: any): boolean => {
    return typeof value === 'object' && value !== null && (value.status === 'failed' || value.status === 'no_data' || value.status === 'error')
  }

  // Helper to get display value for image fields
  const getImageDisplayValue = (value: any): string => {
    if (isImageError(value)) {
      return value.message || `Error: ${value.status}`
    }
    if (typeof value === 'string') return value
    return ''
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {fields.map(field => {
        const rawValue = getNestedValue(data, field.key)
        const isErrorImage = field.type === 'url' && isImageError(rawValue)
        const displayValue = field.type === 'url' ? getImageDisplayValue(rawValue) : rawValue
        const isDisabled = field.disabled || isErrorImage

        return (
          <div key={field.key} className={field.fullWidth ? "col-span-2" : ""}>
            <FormField label={field.label}>
              {field.type === 'select' ? (
                <select
                  value={displayValue}
                  onChange={(e) => onChange(field.key, e.target.value)}
                  disabled={isDisabled}
                  className="w-full rounded-md border border-input bg-input px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select...</option>
                  {field.options?.map((opt: string) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  value={displayValue}
                  onChange={(e) => onChange(field.key, e.target.value)}
                  disabled={isDisabled}
                  className="w-full rounded-md border border-input bg-input px-3 py-2 text-sm min-h-[100px] disabled:opacity-50 disabled:cursor-not-allowed"
                  placeholder={field.label}
                />
              ) : field.type === 'checkbox' ? (
                <div className="flex items-center gap-2 h-10">
                  <input
                    type="checkbox"
                    checked={!!displayValue}
                    onChange={(e) => onChange(field.key, e.target.checked)}
                    disabled={isDisabled}
                    className="w-4 h-4 rounded border-input disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <span className="text-sm text-muted-foreground">{displayValue ? 'Yes' : 'No'}</span>
                </div>
              ) : (
                <Input
                  type={isErrorImage ? 'text' : field.type}
                  step={field.step}
                  value={displayValue}
                  onChange={(e) => onChange(field.key, field.type === 'number' ? parseFloat(e.target.value) || undefined : e.target.value)}
                  disabled={isDisabled}
                  placeholder={field.label}
                  className={`disabled:opacity-50 disabled:cursor-not-allowed ${isErrorImage ? 'text-destructive border-destructive/50' : ''}`}
                />
              )}
            </FormField>
          </div>
        )
      })}
    </div>
  )
}

// Edit Modal
function PropertyEditModal({ property, onSave, onCancel }: { 
  property: Property
  onSave: (data: PropertyUpdate) => void
  onCancel: () => void
}) {
  const [formData, setFormData] = useState<any>({ ...property })

  const handleChange = (key: string, value: any) => {
    // Handle nested keys like "images.aerial"
    if (key.includes('.')) {
      const keys = key.split('.')
      setFormData((prev: any) => {
        const updated = { ...prev }
        let current = updated
        for (let i = 0; i < keys.length - 1; i++) {
          if (!current[keys[i]]) current[keys[i]] = {}
          current[keys[i]] = { ...current[keys[i]] }
          current = current[keys[i]]
        }
        current[keys[keys.length - 1]] = value
        return updated
      })
    } else {
      setFormData((prev: any) => ({ ...prev, [key]: value }))
    }
  }

  const handleSubmit = () => {
    // Clean up the form data - remove undefined/null values but keep nested structures
    const cleanObject = (obj: any): any => {
      if (obj === null || obj === undefined) return undefined
      if (typeof obj !== 'object') return obj
      if (Array.isArray(obj)) return obj
      
      const cleaned: any = {}
      for (const [key, value] of Object.entries(obj)) {
        if (value === null || value === undefined || value === '') continue
        if (typeof value === 'object' && !Array.isArray(value)) {
          const nestedCleaned = cleanObject(value)
          if (nestedCleaned && Object.keys(nestedCleaned).length > 0) {
            cleaned[key] = nestedCleaned
          }
        } else {
          cleaned[key] = value
        }
      }
      return cleaned
    }
    
    const updates = cleanObject(formData)
    console.log('[EDIT] Form data before clean:', formData)
    console.log('[EDIT] Updates being sent:', updates)
    onSave(updates)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <Card className="bg-card border-border w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between sticky top-0 bg-card z-10 border-b">
          <CardTitle className="text-lg tracking-wider">EDIT PROPERTY</CardTitle>
          <Button variant="ghost" size="icon" onClick={onCancel}><X className="w-4 h-4" /></Button>
        </CardHeader>
        <CardContent className="space-y-6 p-6">
           <div><SectionHeader title="BASIC INFORMATION" /><DynamicForm fields={FORM_FIELDS.basic} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="LOCATION" /><DynamicForm fields={FORM_FIELDS.location} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="PROPERTY DETAILS" /><DynamicForm fields={FORM_FIELDS.details} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="PRICING" /><DynamicForm fields={FORM_FIELDS.pricing} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="CONTACTS" /><DynamicForm fields={FORM_FIELDS.contacts} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="SOURCE DATA (LISTING INFO)" /><DynamicForm fields={FORM_FIELDS.sourceData} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="OWNER INFORMATION" /><DynamicForm fields={FORM_FIELDS.owner} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="PARCEL DATA" /><DynamicForm fields={FORM_FIELDS.parcel} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="IMAGES" /><DynamicForm fields={FORM_FIELDS.images} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="ANALYSIS SUMMARY" /><DynamicForm fields={FORM_FIELDS.analysisSummary} data={formData} onChange={handleChange} /></div>
           <div><SectionHeader title="METADATA" /><DynamicForm fields={FORM_FIELDS.metadata} data={formData} onChange={handleChange} /></div>

          <div className="flex gap-2 sticky bottom-0 bg-card pt-4 border-t">
            <Button onClick={handleSubmit} className="bg-primary">Save Changes</Button>
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
// View Modal
function PropertyViewModal({ property, onEdit, onDelete, onClose }: {
  property: Property
  onEdit: () => void
  onDelete: () => void
  onClose: () => void
}) {
  const propertyUrl = buildPropertyUrl(property)
  const analysis = property.analysis as any
  const sourceData = property.source_data as any
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <Card className="bg-card border-border w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-bold tracking-wider">{property.situs_addr || `Property ${property.gid}`}</CardTitle>
            <p className="text-sm text-muted-foreground font-mono">ID: {property.property_id}</p>
          </div>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {propertyUrl && (
            <div className="p-3 bg-muted rounded-md flex items-center justify-between">
              <span className="text-sm text-muted-foreground">View on website</span>
              <Button variant="outline" size="sm" asChild>
                <a href={propertyUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />Open
                </a>
              </Button>
            </div>
          )}
          
          <div><SectionHeader title="BASIC INFORMATION" />
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="PROPERTY ID" value={property.property_id} />
              <InfoField label="GID" value={property.gid} />
              <InfoField label="STATUS" value={property.status} />
              <InfoField label="PROPERTY TYPE" value={sourceData?.Type} />
            </div>
          </div>
          
          <div><SectionHeader title="LOCATION" />
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2"><InfoField label="ADDRESS" value={property.situs_addr} /></div>
              <InfoField label="COUNTY" value={property.county} />
              <InfoField label="CITY" value={property.city} />
              <InfoField label="STATE" value={sourceData?.State} />
              <InfoField label="ZIP" value={sourceData?.Zip} />
              <InfoField label="LATITUDE" value={property.latitude} />
              <InfoField label="LONGITUDE" value={property.longitude} />
            </div>
          </div>

          <div><SectionHeader title="PROPERTY DETAILS" />
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="ACREAGE" value={property.acreage ? `${property.acreage.toFixed(2)} ac` : undefined} />
              <InfoField label="LOT SIZE" value={sourceData?.LotSize ? `${sourceData.LotSize.toLocaleString()} sq ft` : undefined} />
              <InfoField label="BEDROOMS" value={sourceData?.Beds || undefined} />
              <InfoField label="BATHROOMS" value={sourceData?.Baths || undefined} />
              <InfoField label="YEAR BUILT" value={sourceData?.BuiltIn || undefined} />
              <InfoField label="FLOOR SIZE" value={sourceData?.FloorSize || undefined} />
            </div>
          </div>

          <div><SectionHeader title="PRICING" />
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="PRICE" value={property.sell_price ? `$${property.sell_price.toLocaleString()}` : undefined} />
              <InfoField label="PRICE PER ACRE" value={property.price_per_acre ? `$${property.price_per_acre.toLocaleString()}` : undefined} />
              <InfoField label="DAYS ON MARKET" value={sourceData?.DaysOnMarket} />
            </div>
          </div>

          <div><SectionHeader title="CONTACTS" />
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="AGENT NAME" value={property.seller_name || sourceData?.AgentName} />
              <InfoField label="AGENT EMAIL" value={sourceData?.AgentEmail} />
              <InfoField label="AGENT PHONE" value={sourceData?.AgentPhone} />
              <InfoField label="AGENT OFFICE" value={sourceData?.AgentOffice} />
            </div>
          </div>

          {analysis?.parcels && (
            <div><SectionHeader title="PARCEL DATA" />
              <div className="grid grid-cols-2 gap-4">
                <InfoField label="GEO ID" value={analysis.parcels.geo_id} />
                <InfoField label="PARCEL PROP ID" value={analysis.parcels.prop_id} />
                <InfoField label="OWNER NAME" value={analysis.parcels.owner_name} />
                <InfoField label="PARCEL ACREAGE" value={analysis.parcels.acreage?.toFixed(3)} />
                <div className="col-span-2"><InfoField label="PARCEL ADDRESS" value={analysis.parcels.situs_addr} /></div>
              </div>
            </div>
          )}

          {sourceData && (sourceData.PartyOwner1NameFull || sourceData.ContactOwnerMailAddressFull) && (
            <div><SectionHeader title="OWNER INFORMATION" />
              <div className="grid grid-cols-2 gap-4">
                {sourceData.PartyOwner1NameFull && <InfoField label="OWNER 1" value={sourceData.PartyOwner1NameFull} />}
                {sourceData.PartyOwner2NameFull && <InfoField label="OWNER 2" value={sourceData.PartyOwner2NameFull} />}
                {sourceData.PartyOwner3NameFull && <InfoField label="OWNER 3" value={sourceData.PartyOwner3NameFull} />}
                {sourceData.ContactOwnerMailAddressFull && (
                  <div className="col-span-2"><InfoField label="OWNER MAIL ADDRESS" value={`${sourceData.ContactOwnerMailAddressFull}, ${sourceData.ContactOwnerMailAddressCity}, ${sourceData.ContactOwnerMailAddressState} ${sourceData.ContactOwnerMailAddressZIP}`} /></div>
                )}
              </div>
            </div>
          )}

          {analysis && (
            <div><SectionHeader title="IMAGES" />
              <div className="grid grid-cols-1 gap-2">
                {analysis.image_url && typeof analysis.image_url === 'string' && <InfoField label="AERIAL" value={analysis.image_url} />}
                {analysis.contour_image_url && typeof analysis.contour_image_url === 'string' && <InfoField label="CONTOUR" value={analysis.contour_image_url} />}
                {analysis.flood_image_url && typeof analysis.flood_image_url === 'string' && <InfoField label="FLOOD" value={analysis.flood_image_url} />}
                {analysis.road_frontage_image_url && typeof analysis.road_frontage_image_url === 'string' && <InfoField label="ROAD FRONTAGE" value={analysis.road_frontage_image_url} />}
                {analysis.tree_image_url && typeof analysis.tree_image_url === 'string' && <InfoField label="TREE" value={analysis.tree_image_url} />}
                {analysis.water_image_url && typeof analysis.water_image_url === 'string' && <InfoField label="WATER" value={analysis.water_image_url} />}
              </div>
            </div>
          )}

          {analysis && (
            <div><SectionHeader title="ANALYSIS DATA" />
              <div className="grid grid-cols-2 gap-4">
                {analysis.buildable_area && (
                  <InfoField label="BUILDABLE AREA" value={formatBuildableArea(analysis.buildable_area)} />
                )}
                {analysis.flood_hazard && <InfoField label="FLOOD HAZARD" value={formatFloodHazard(analysis.flood_hazard)} />}
                {analysis.electric_lines && <InfoField label="ELECTRIC LINES" value={formatElectricLines(analysis.electric_lines)} />}
                {analysis.gas_lines && <InfoField label="GAS LINES" value={formatGasLines(analysis.gas_lines)} />}
                {analysis.road_analysis && <div className="col-span-2"><InfoField label="ROAD ANALYSIS" value={formatRoadAnalysis(analysis.road_analysis)} /></div>}
                {analysis.well_analysis && <div className="col-span-2"><InfoField label="WELL ANALYSIS" value={formatWellAnalysis(analysis.well_analysis)} /></div>}
                {analysis.wetland_analysis && <div className="col-span-2"><InfoField label="WETLAND ANALYSIS" value={formatWetlandAnalysis(analysis.wetland_analysis)} /></div>}
                {analysis.lake_analysis && <div className="col-span-2"><InfoField label="LAKE ANALYSIS" value={formatLakeAnalysis(analysis.lake_analysis)} /></div>}
                {analysis.pond_analysis && <div className="col-span-2"><InfoField label="POND ANALYSIS" value={formatPondAnalysis(analysis.pond_analysis)} /></div>}
                {analysis.stream_intersection && <InfoField label="STREAM INTERSECTION" value={formatStreamIntersection(analysis.stream_intersection)} />}
                {analysis.shoreline_analysis && <div className="col-span-2"><InfoField label="SHORELINE ANALYSIS" value={formatShorelineAnalysis(analysis.shoreline_analysis)} /></div>}
                {analysis.tree_coverage && (
                  <InfoField label="TREE COVERAGE" value={formatTreeCoverage(analysis.tree_coverage)} />
                )}
                {analysis.elevation_change && (
                  <InfoField label="ELEVATION CHANGE" value={formatElevationChange(analysis.elevation_change)} />
                )}
              </div>
            </div>
          )}

          <div><SectionHeader title="METADATA" />
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="CREATED AT" value={property.created_at ? new Date(property.created_at).toLocaleString() : undefined} />
              <InfoField label="UPDATED AT" value={property.updated_at ? new Date(property.updated_at).toLocaleString() : undefined} />
              {analysis?.meta && (
                <>
                  <InfoField label="BATCH ID" value={analysis.meta.batch_id} />
                  <InfoField label="PROCESSING MODE" value={analysis.meta.processing_mode} />
                  <InfoField label="EXECUTION TIME" value={analysis.meta.execution_time_seconds ? `${analysis.meta.execution_time_seconds}s` : undefined} />
                </>
              )}
            </div>
          </div>
          
          <div className="flex gap-2 pt-4">
            <Button onClick={onEdit} className="bg-primary"><Edit className="w-4 h-4 mr-2" />Edit</Button>
            <Button variant="outline" onClick={onDelete} className="border-destructive text-destructive"><Trash2 className="w-4 h-4 mr-2" />Delete</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Main Component
export default function PropertyCataloguePage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [properties, setProperties] = useState<Property[]>([])
  const [filteredProperties, setFilteredProperties] = useState<Property[]>([])
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statistics, setStatistics] = useState<PropertyStatistics | null>(null)
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive" | "activelisting">("all")
  const [isEditMode, setIsEditMode] = useState(false)
  const [isCreateMode, setIsCreateMode] = useState(false)
  // CHANGED: Default mode
  const [queryMode, setQueryMode] = useState<QueryMode>("in-memory-current")
  const [hasMore, setHasMore] = useState(true)
  const [offset, setOffset] = useState(0)
  const observerTarget = useRef<HTMLDivElement>(null)

  useEffect(() => { loadProperties(); loadStatistics() }, [])
  // CHANGED: Trigger on dynamodb mode
  useEffect(() => { queryMode === "dynamodb" ? loadPropertiesDynamo() : filterPropertiesInMemory() }, [searchTerm, statusFilter, queryMode])
  
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !isLoadingMore && !isLoading) loadMoreProperties()
    }, { threshold: 0.1 })
    if (observerTarget.current) observer.observe(observerTarget.current)
    return () => observer.disconnect()
  }, [hasMore, isLoadingMore, isLoading, offset])

  const filterPropertiesInMemory = () => {
    let filtered = properties
    if (statusFilter !== "all") filtered = filtered.filter(p => p.status === statusFilter)
    if (searchTerm) {
      const s = searchTerm.toLowerCase()
      filtered = filtered.filter(p => 
        p.owner_name?.toLowerCase().includes(s) || p.prop_id?.toLowerCase().includes(s) || 
        p.county?.toLowerCase().includes(s) || p.user_name?.toLowerCase().includes(s) || p.seller_name?.toLowerCase().includes(s)
      )
    }
    setFilteredProperties(filtered)
  }

  const loadProperties = async () => {
    try {
      setIsLoading(true); setError(null); setOffset(0); setHasMore(true)
      const data = await gisApi.listProperties({ limit: 500, desc: true })
      const propertiesArray = data?.properties || []
      setProperties(propertiesArray); setFilteredProperties(propertiesArray)
      setHasMore(data?.has_more || false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load properties")
    } finally {
      setIsLoading(false)
    }
  }

  const loadMoreProperties = async () => {
    if (!hasMore || isLoadingMore) return
    try {
      setIsLoadingMore(true)
      const newOffset = offset + 500
      const data = await gisApi.listProperties({ limit: 500, desc: true, offset: newOffset })
      const propertiesArray = data?.properties || []
      if (propertiesArray.length === 0) { setHasMore(false); return }
      setProperties(prev => [...prev, ...propertiesArray]); setOffset(newOffset)
      setHasMore(data?.has_more || false)
      // CHANGED: Check logic against dynamodb
      if (queryMode !== "dynamodb") filterPropertiesInMemory()
    } catch (err) {
      console.error("Error loading more:", err)
    } finally {
      setIsLoadingMore(false)
    }
  }

  // CHANGED: Renamed function for clarity
  const loadPropertiesDynamo = async () => {
    try {
      setIsLoading(true); setError(null)
      const params: any = { limit: 500, offset: 0 }
      if (statusFilter !== "all") params.status = statusFilter
      if (searchTerm) {
        const result = await gisApi.searchProperties({ ...params, owner_name: searchTerm })
        setFilteredProperties(Array.isArray(result.properties) ? result.properties : []); setHasMore(result.has_more)
      } else {
        const data = await gisApi.listProperties(params)
        const propertiesArray = data?.properties || []
        setFilteredProperties(propertiesArray); setHasMore(data?.has_more || false)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load properties")
    } finally {
      setIsLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const stats = await gisApi.getPropertyStatistics()
      setStatistics(stats)
    } catch (err) {
      console.error("Error loading statistics:", err)
      // Don't block the UI if stats fail
    }
  }

  const handleSaveProperty = async (data: PropertyUpdate) => {
    // CHANGED: Using property_id
    if (!selectedProperty || !selectedProperty.property_id) return
    try {
      const updatedProperty = await gisApi.updateProperty(selectedProperty.property_id, data)
      
      // Update the property in local state instead of refetching all
      setProperties(prev => prev.map(p => 
        p.property_id === updatedProperty.property_id ? updatedProperty : p
      ))
      setFilteredProperties(prev => prev.map(p => 
        p.property_id === updatedProperty.property_id ? updatedProperty : p
      ))
      
      setIsEditMode(false); setSelectedProperty(null)
      await loadStatistics() // Just refresh stats
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update property")
    }
  }

  const handleDeleteProperty = async () => {
    // CHANGED: Using property_id
    if (!selectedProperty || !selectedProperty.property_id || !confirm("Are you sure you want to delete this property?")) return
    try {
      await gisApi.deleteProperty(selectedProperty.property_id)
      setSelectedProperty(null)
      await loadProperties(); await loadStatistics()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete property")
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* ... [Header Section] ... */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-wider">PROPERTY CATALOGUE</h1>
          <p className="text-sm text-muted-foreground">Manage and search property inventory</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setIsCreateMode(true)} className="bg-primary hover:bg-primary/90"><Plus className="w-4 h-4 mr-2" />Add Property</Button>
          <Button onClick={loadProperties} className="bg-primary hover:bg-primary/90">Refresh</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input placeholder="Search properties..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10 bg-input border-input" />
            </div>
            {/* ... [Status Filters] ... */}
             <div className="mt-3 flex gap-2">
              {['all', 'active', 'inactive'].map(s => (
                <Button key={s} size="sm" variant={statusFilter === s ? "default" : "outline"} onClick={() => setStatusFilter(s as any)} className="flex-1 text-xs">{s.toUpperCase()}</Button>
              ))}
            </div>
            <div className="mt-3">
              <label className="text-xs text-muted-foreground mb-1 block">QUERY MODE</label>
              {/* CHANGED: Option values and labels */}
              <select value={queryMode} onChange={(e) => setQueryMode(e.target.value as QueryMode)} className="w-full rounded-md border border-input bg-input px-3 py-2 text-xs">
                <option value="in-memory-current">In-Memory (Current)</option>
                <option value="in-memory-all">In-Memory (Fetch All)</option>
                <option value="dynamodb">DynamoDB Query</option>
              </select>
            </div>
          </CardContent>
        </Card>
        
        {/* ... [Statistics Cards (keep as is)] ... */}
        <Card className="bg-card border-border"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground tracking-wider">TOTAL</p><p className="text-2xl font-bold font-mono">{statistics?.total_properties || 0}</p></div><Home className="w-8 h-8 text-foreground" /></div></CardContent></Card>
        <Card className="bg-card border-border"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground tracking-wider">ACTIVE</p><p className="text-2xl font-bold font-mono text-primary">{statistics?.active_properties || 0}</p></div><Home className="w-8 h-8 text-primary" /></div></CardContent></Card>
        <Card className="bg-card border-border"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground tracking-wider">TOTAL ACRES</p><p className="text-2xl font-bold font-mono">{statistics?.total_acres?.toFixed(0) || 0}</p></div><MapPin className="w-8 h-8 text-foreground" /></div></CardContent></Card>
      </div>

      {error && <Card className="bg-destructive/10 border-destructive"><CardContent className="p-4"><p className="text-destructive">{error}</p></CardContent></Card>}

      <Card className="bg-card border-border">
        <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground tracking-wider">PROPERTY INVENTORY ({filteredProperties.length})</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <div className="text-center py-8 text-muted-foreground">Loading...</div> : 
           filteredProperties.length === 0 ? <div className="text-center py-8 text-muted-foreground">No properties found</div> :
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    {/* ... [Headers] ... */}
                    {['PROPERTY ID', 'BATCH ID', 'OWNER', 'STATUS', 'COUNTY', 'ACRES', 'PRICE', 'USER', 'ACTIONS'].map(h => (
                      <th key={h} className="text-left py-3 px-4 text-xs font-medium text-muted-foreground tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredProperties.map((p, i) => (
                    // CHANGED: key to p.property_id
                    <tr key={p.property_id || i} className={`border-b border-border hover:bg-muted transition-colors cursor-pointer ${i % 2 === 0 ? "bg-card" : "bg-muted/30"}`} onClick={() => setSelectedProperty(p)}>
                      <td className="py-3 px-4 text-sm font-mono">{p.prop_id || p.gid || "N/A"}</td>
                      <td className="py-3 px-4 text-sm font-mono">{(p.analysis as any)?.meta?.batch_id || "N/A"}</td>
                      <td className="py-3 px-4 text-sm">{p.owner_name || "Unknown"}</td>
                      <td className="py-3 px-4"><div className="flex items-center gap-2"><div className={`w-2 h-2 rounded-full ${p.status === "active" ? "bg-primary" : "bg-muted-foreground"}`} /><span className="text-xs uppercase tracking-wider">{p.status}</span></div></td>
                      <td className="py-3 px-4 text-sm">{p.county || "N/A"}</td>
                      <td className="py-3 px-4 text-sm font-mono">{p.acreage ? `${p.acreage.toFixed(2)} ac` : "N/A"}</td>
                      <td className="py-3 px-4 text-sm font-mono">{p.sell_price ? `$${p.sell_price.toLocaleString()}` : "N/A"}</td>
                      <td className="py-3 px-4 text-sm">{p.user_name || "N/A"}</td>
                      <td className="py-3 px-4">
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setSelectedProperty(p); setIsEditMode(true) }}><Edit className="w-4 h-4" /></Button>
                          <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setSelectedProperty(p); handleDeleteProperty() }}><Trash2 className="w-4 h-4" /></Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
               {/* ... [Keep Pagination Logic] ... */}
               {hasMore && queryMode === "in-memory-current" && (
                <div ref={observerTarget} className="py-4 text-center">
                  {isLoadingMore ? <div className="flex items-center justify-center gap-2 text-muted-foreground"><RefreshCw className="w-4 h-4 animate-spin" /><span>Loading more...</span></div> : <div className="text-muted-foreground text-sm">Scroll for more</div>}
                </div>
              )}
              {!hasMore && properties.length > 0 && <div className="py-4 text-center text-muted-foreground text-sm">All properties loaded ({properties.length} total)</div>}
            </div>
          }
        </CardContent>
      </Card>

      {selectedProperty && !isEditMode && <PropertyViewModal property={selectedProperty} onEdit={() => setIsEditMode(true)} onDelete={handleDeleteProperty} onClose={() => setSelectedProperty(null)} />}
      {selectedProperty && isEditMode && <PropertyEditModal property={selectedProperty} onSave={handleSaveProperty} onCancel={() => { setIsEditMode(false); setSelectedProperty(null) }} />}
      {isCreateMode && <AddPropertyModal onClose={() => setIsCreateMode(false)} onPropertyAdded={() => { setIsCreateMode(false); loadProperties() }} />}
    </div>
  )
}