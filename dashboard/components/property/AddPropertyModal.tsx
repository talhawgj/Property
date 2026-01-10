"use client"

import React, { useState } from 'react'
import { X, Search, MapPin, DollarSign, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import axios from 'axios'

interface AddPropertyModalProps {
  onClose: () => void
  onPropertyAdded: () => void
}

type SearchType = 'property_id' | 'owner_name' | 'coordinates'

interface ParcelData {
  gid?: number
  prop_id?: string
  geo_id?: string
  owner_name?: string
  situs_addr?: string
  county?: string
  acreage?: number
  latitude?: number
  longitude?: number
  [key: string]: any
}

type AnalysisResult = Record<string, any>

type AnalysisStatus = 'idle' | 'running' | 'done' | 'error'

export function AddPropertyModal({ onClose, onPropertyAdded }: AddPropertyModalProps) {
  const [searchType, setSearchType] = useState<SearchType>('property_id')
  const [propId, setPropId] = useState('')
  const [county, setCounty] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [ownerCounty, setOwnerCounty] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [price, setPrice] = useState('')
  const [error, setError] = useState('')
  const [searching, setSearching] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('idle')
  const [analysisGid, setAnalysisGid] = useState<number | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [adding, setAdding] = useState(false)
  const [foundParcels, setFoundParcels] = useState<ParcelData[]>([])
  const [selectedParcel, setSelectedParcel] = useState<ParcelData | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const API_KEY = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_API_KEY || ""

  const handleSearch = async () => {
    setError('')
    setFoundParcels([])
    setSelectedParcel(null)
    setAnalysisStatus('idle')
    setAnalysisGid(null)
    setAnalysisResult(null)
    setSearching(true)

    try {
      let response
      
      if (searchType === 'property_id') {
        if (!propId.trim()) {
          setError('Please enter a Property ID or Geo ID')
          setSearching(false)
          return
        }
        response = await axios.get(`${API_BASE_URL}/search/parcel`, {
          params: { prop_id: propId, county: county || undefined },
          headers: { 'x-api-key': API_KEY }
        })
      } else if (searchType === 'owner_name') {
        if (!ownerName.trim() || !ownerCounty.trim()) {
          setError('Please enter both Owner Name and County')
          setSearching(false)
          return
        }
        response = await axios.get(`${API_BASE_URL}/search/parcel/owner`, {
          params: { owner_name: ownerName, county: ownerCounty },
          headers: { 'x-api-key': API_KEY }
        })
      } else if (searchType === 'coordinates') {
        if (!latitude || !longitude) {
          setError('Please enter both Latitude and Longitude')
          setSearching(false)
          return
        }
        response = await axios.get(`${API_BASE_URL}/search/parcel/coordinates`, {
          params: { latitude, longitude },
          headers: { 'x-api-key': API_KEY }
        })
      }

      let parcels: ParcelData[] = []
      if (response?.data?.parcels) {
        parcels = Array.isArray(response.data.parcels) ? response.data.parcels : [response.data.parcels]
      } else if (Array.isArray(response?.data)) {
        parcels = response.data
      }

      if (parcels.length === 0) {
        setError('No parcels found')
      } else {
        setFoundParcels(parcels)
        if (parcels.length === 1) {
          setSelectedParcel(parcels[0])
          setAnalysisStatus('idle')
          setAnalysisGid(null)
          setAnalysisResult(null)
        }
      }
    } catch (err: any) {
      console.error('Search Error:', err)
      setError(err.response?.data?.error || err.response?.data?.detail || 'Error searching parcels')
    } finally {
      setSearching(false)
    }
  }

  const handleRunAnalysis = async () => {
    setError('')

    if (!selectedParcel) {
      setError('Please select a parcel')
      return
    }

    if (!selectedParcel.gid && selectedParcel.gid !== 0) {
      setError('Selected parcel is missing a GID; cannot run analysis')
      return
    }

    const gid = selectedParcel.gid
    setAnalysisStatus('running')
    setAnalysisGid(gid)
    setAnalysisResult(null)

    try {
      const res = await axios.get(`${API_BASE_URL}/analyze/${gid}`, {
        params: { persist: false },
        headers: { 'x-api-key': API_KEY }
      })

      if (res?.data?.error) {
        setError(res.data.error)
        setAnalysisStatus('error')
        return
      }

      // If the user has switched parcels while analysis was running, ignore this response.
      setAnalysisResult(res.data)
      console.log(analysisResult)
      setAnalysisStatus('done')
    } catch (err: any) {
      console.error('Analysis Error:', err)
      setError(err.response?.data?.error || err.response?.data?.detail || 'Error running analysis')
      setAnalysisStatus('error')
    } finally {
      // Note: analysisStatus remains 'running' until we explicitly set 'done'/'error'
    }
  }

  const handleAddProperty = async () => {
    if (!selectedParcel) {
      setError('Please select a parcel')
      return
    }

    if (analysisStatus !== 'done' || !analysisResult || analysisGid !== selectedParcel.gid) {
      setError('Please run analysis and wait for results before adding to catalogue')
      return
    }

    if (!price || parseFloat(price) <= 0) {
      setError('Please enter a valid price')
      return
    }

    setAdding(true)
    setError('')

    try {
      const propertyData = {
        gid: selectedParcel.gid,
        prop_id: selectedParcel.prop_id,
        county: selectedParcel.county,
        owner_name: selectedParcel.owner_name,
        situs_addr: selectedParcel.situs_addr,
        acreage: selectedParcel.acreage,
        latitude: selectedParcel.latitude,
        longitude: selectedParcel.longitude,
        sell_price: parseFloat(price),
        price_per_acre: selectedParcel.acreage ? parseFloat(price) / selectedParcel.acreage : undefined,
        status: 'activelisting',
        user_name: 'admin', // You can modify this to use actual user context
        analysis: analysisResult,
      }

      await axios.post(
        `${API_BASE_URL}/catalogue/properties`,
        propertyData,
        {
          headers: {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json'
          }
        }
      )

      onPropertyAdded()
      onClose()
    } catch (err: any) {
      console.error('Add Property Error:', err)
      setError(err.response?.data?.detail || 'Error adding property to catalogue')
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="bg-card border-border w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div>
            <h2 className="text-2xl font-bold text-foreground tracking-wider">ADD PROPERTY</h2>
            <p className="text-sm text-muted-foreground mt-1">Search for a property and add it to the catalogue</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Search Type Selector */}
          <div>
            <label className="text-xs text-muted-foreground tracking-wider mb-2 block">SEARCH TYPE</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'property_id', label: 'Property ID', icon: MapPin },
                { value: 'owner_name', label: 'Owner Name', icon: Search },
                { value: 'coordinates', label: 'Coordinates', icon: MapPin }
              ].map(({ value, label, icon: Icon }) => (
                <Button
                  key={value}
                  variant={searchType === value ? 'default' : 'outline'}
                  onClick={() => setSearchType(value as SearchType)}
                  className="justify-start"
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {label}
                </Button>
              ))}
            </div>
          </div>

          {/* Search Fields */}
          <div className="space-y-4">
            {searchType === 'property_id' && (
              <>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">PROPERTY ID / GEO ID / APN</label>
                  <Input
                    value={propId}
                    onChange={(e) => setPropId(e.target.value)}
                    placeholder="Enter Property ID, Geo ID, or APN"
                    className="bg-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">COUNTY (OPTIONAL)</label>
                  <Input
                    value={county}
                    onChange={(e) => setCounty(e.target.value)}
                    placeholder="e.g., Travis, Harris"
                    className="bg-input"
                  />
                </div>
              </>
            )}

            {searchType === 'owner_name' && (
              <>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">OWNER NAME</label>
                  <Input
                    value={ownerName}
                    onChange={(e) => setOwnerName(e.target.value)}
                    placeholder="e.g., Smith, Johnson"
                    className="bg-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">COUNTY (REQUIRED)</label>
                  <Input
                    value={ownerCounty}
                    onChange={(e) => setOwnerCounty(e.target.value)}
                    placeholder="e.g., Travis, Harris"
                    className="bg-input"
                  />
                </div>
              </>
            )}

            {searchType === 'coordinates' && (
              <>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">LATITUDE</label>
                  <Input
                    type="number"
                    step="0.000001"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="e.g., 30.2672"
                    className="bg-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground tracking-wider mb-1 block">LONGITUDE</label>
                  <Input
                    type="number"
                    step="0.000001"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="e.g., -97.7431"
                    className="bg-input"
                  />
                </div>
              </>
            )}

            {/* Price Field - Always Visible */}
            <div>
              <label className="text-xs text-muted-foreground tracking-wider mb-1 flex items-center">
                <DollarSign className="w-4 h-4 mr-1" />
                LISTING PRICE (REQUIRED)
              </label>
              <Input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="Enter listing price"
                className="bg-input"
              />
            </div>
          </div>

          {/* Search Button */}
          <Button
            onClick={handleSearch}
            disabled={searching}
            className="w-full bg-primary hover:bg-primary/90"
          >
            {searching ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                Search Property
              </>
            )}
          </Button>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive rounded-md">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Search Results */}
          {foundParcels.length > 0 && (
            <div>
              <label className="text-xs text-muted-foreground tracking-wider mb-2 block">
                FOUND {foundParcels.length} PARCEL{foundParcels.length > 1 ? 'S' : ''}
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {foundParcels.map((parcel, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      setSelectedParcel(parcel)
                      setAnalysisStatus('idle')
                      setAnalysisGid(null)
                      setAnalysisResult(null)
                      setError('')
                    }}
                    className={`p-4 border rounded-md cursor-pointer transition-all ${
                      selectedParcel === parcel
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50 bg-card'
                    }`}
                  >
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Property ID</p>
                        <p className="font-mono">{parcel.prop_id || parcel.geo_id || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">County</p>
                        <p>{parcel.county || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Owner</p>
                        <p>{parcel.owner_name || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Acreage</p>
                        <p>{parcel.acreage?.toFixed(2) || 'N/A'}</p>
                      </div>
                      {parcel.situs_addr && (
                        <div className="col-span-2">
                          <p className="text-xs text-muted-foreground">Address</p>
                          <p className="text-xs">{parcel.situs_addr}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>

          {analysisStatus !== 'done' || !analysisResult || analysisGid !== selectedParcel?.gid ? (
            <Button
              onClick={handleRunAnalysis}
              disabled={!selectedParcel || analysisStatus === 'running'}
              className="bg-primary hover:bg-primary/90"
            >
              {analysisStatus === 'running' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Running Analysis...
                </>
              ) : (
                'Run Analysis'
              )}
            </Button>
          ) : (
            <Button
              onClick={handleAddProperty}
              disabled={!selectedParcel || !price || adding}
              className="bg-primary hover:bg-primary/90"
            >
              {adding ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add to Catalogue'
              )}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
