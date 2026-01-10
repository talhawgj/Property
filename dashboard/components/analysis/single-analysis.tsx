"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import api from "@/lib/api"
import { 
  Container, 
  Typography, 
  CircularProgress, 
  Card, 
  CardContent, 
  CardMedia, 
  Button, 
  Box
} from "@mui/material"
import { useAnalysis } from "@/contexts/analysis-context"

interface Property {
  gid: string
  owner_name: string
  situs_addr: string
  county: string
  [key: string]: any
}

export function SingleAnalysis() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { singleState, setSingleState } = useAnalysis()
  
  const searchType = searchParams.get("search_type")
  const propId = searchParams.get("prop_id")
  const county = searchParams.get("county")
  const ownerName = searchParams.get("owner_name")
  const latitude = searchParams.get("latitude")
  const longitude = searchParams.get("longitude")

  // Use state from context if available, otherwise initialize
  const [properties, setProperties] = useState<Property[]>(singleState?.properties || [])
  const [loading, setLoading] = useState<boolean>(singleState?.loading ?? true)
  const [parcelImages, setParcelImages] = useState<Record<string, string>>(singleState?.parcelImages || {})
  const [imageErrors, setImageErrors] = useState<Record<string, string>>(singleState?.imageErrors || {})
  const [rerunLoading, setRerunLoading] = useState<Record<string, boolean>>({})

  // Save state to context whenever it changes
  useEffect(() => {
    setSingleState({
      properties,
      loading,
      parcelImages,
      imageErrors,
      searchParams: {
        searchType,
        propId,
        county,
        ownerName,
        latitude,
        longitude
      }
    })
  }, [properties, loading, parcelImages, imageErrors, searchType, propId, county, ownerName, latitude, longitude, setSingleState])

  // Handler for re-running analysis
  const rerunAnalysis = async (gid: string) => {
    setRerunLoading((prev) => ({ ...prev, [gid]: true }))
    setLoading(true)
    try {
      await api.post(`/analyze/rerun/${gid}`)
      const response = await api.get(`/analyze/${gid}`)
      let fetchedProperties: Property[] = []
      
      if (Array.isArray(response.data)) {
        fetchedProperties = response.data
      } else if (response.data.parcels) {
        if (Array.isArray(response.data.parcels)) {
          fetchedProperties = response.data.parcels
        } else {
          fetchedProperties = [response.data.parcels]
        }
      } else if (response.data) {
        fetchedProperties = [response.data]
      }
      
      setProperties(fetchedProperties)
      fetchParcelImage(gid)
      console.log("[RERUN] Updated properties state:", fetchedProperties)
    } catch (error) {
      console.error(`[RERUN] Error re-running analysis for GID ${gid}:`, error)
    } finally {
      setRerunLoading((prev) => ({ ...prev, [gid]: false }))
      setLoading(false)
    }
  }

  useEffect(() => {
    // If we have state from context and search params match, don't refetch
    if (singleState?.properties?.length > 0 && 
        singleState.searchParams?.searchType === searchType &&
        singleState.searchParams?.propId === propId &&
        singleState.searchParams?.ownerName === ownerName &&
        singleState.searchParams?.latitude === latitude &&
        singleState.searchParams?.longitude === longitude) {
      // Use cached state
      setLoading(false)
      return
    }

    // Otherwise fetch fresh data
    const fetchProperties = async () => {
      try {
        let response
        if (searchType === "property_id" && propId && county) {
          response = await api.get(`/search/parcel?prop_id=${propId}&county=${county}`)
        } else if (searchType === "owner_name" && ownerName) {
          response = await api.get(`/search/parcel/owner?owner_name=${ownerName}`)
        } else if (searchType === "coordinates" && latitude && longitude) {
          response = await api.get(`/search/parcel/coordinates?latitude=${latitude}&longitude=${longitude}`)
        }

        console.log("API Response:", response?.data)

        let fetchedProperties: Property[] = []
        if (response) {
          if (Array.isArray(response.data)) {
            fetchedProperties = response.data
          } else if (response.data.parcels) {
            fetchedProperties = response.data.parcels
          } else if (response.data.message) {
            console.log("No parcels found:", response.data.message)
            setLoading(false)
            return
          }
        }

        console.log("Fetched Properties:", fetchedProperties)
        setProperties(fetchedProperties)
        setLoading(false)

        fetchedProperties.forEach((property) => {
          fetchParcelImage(property.gid)
        })
      } catch (error) {
        console.error("Error fetching properties:", error)
        setLoading(false)
      }
    }

    if (searchType && (propId || ownerName || (latitude && longitude))) {
      fetchProperties()
    } else {
      setLoading(false)
    }
  }, [searchType, propId, county, ownerName, latitude, longitude])

  const fetchParcelImage = async (gid: string) => {
    try {
      const timestamp = new Date().getTime()
      const response = await api.get(`/analysis/image/parcel/${gid}?t=${timestamp}`)
      const imageUrl = response.data.image_url

      console.log(`Fetched image URL for GID ${gid}:`, imageUrl)

      setParcelImages((prev) => ({
        ...prev,
        [gid]: imageUrl,
      }))
      setImageErrors((prev) => ({
        ...prev,
        [gid]: "",
      }))
    } catch (error) {
      console.error(`Error fetching parcel image for GID ${gid}:`, error)
      setImageErrors((prev) => ({
        ...prev,
        [gid]: "Failed to load image",
      }))
    }
  }

  console.log("Current properties state:", properties)

  if (loading) return <CircularProgress />
  if (properties.length === 0) return <Typography variant="h6">No properties found</Typography>

  return (
    <Container maxWidth="lg" className="property-container">
      <Typography variant="h4" gutterBottom align="center" className="page-title">
        Select a Property
      </Typography>

      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 3,
        justifyContent: 'center'
      }}>
        {properties.map((property) => (
          <Box
            key={property.gid}
            className="property-card"
            sx={{
              display: "flex",
              justifyContent: "center",
            }}
          >
            <Card
              sx={{
                width: "100%",
                maxWidth: "320px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                overflow: "hidden",
              }}
            >
              {parcelImages[property.gid] ? (
                <CardMedia
                  component="img"
                  height="200"
                  image={parcelImages[property.gid]}
                  alt={`Parcel Screenshot for GID ${property.gid}`}
                  sx={{
                    objectFit: "cover",
                    width: "100%",
                    height: "180",
                    borderRadius: "4px",
                  }}
                />
              ) : imageErrors[property.gid] ? (
                <Box
                  sx={{
                    width: "100%",
                    height: "180px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: "#f0f0f0",
                    borderRadius: "4px",
                  }}
                >
                  <Typography color="error">{imageErrors[property.gid]}</Typography>
                </Box>
              ) : (
                <Box
                  sx={{
                    width: "100%",
                    height: "180px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: "#f0f0f0",
                    borderRadius: "4px",
                  }}
                >
                  <CircularProgress size={24} />
                </Box>
              )}
              <CardContent sx={{ textAlign: "center", width: "100%" }}>
                <Typography variant="h6" sx={{ fontWeight: "bold" }}>
                  Owner: {property.owner_name}
                </Typography>
                <Typography>Address: {property.situs_addr}</Typography>
                <Typography>County: {property.county}</Typography>
                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  sx={{ marginTop: "10px" }}
                  onClick={() => router.push(`/property-details/${property.gid}`)}
                >
                  View Details
                </Button>
                <Button
                  variant="outlined"
                  color="secondary"
                  fullWidth
                  sx={{ marginTop: "10px" }}
                  onClick={() => rerunAnalysis(property.gid)}
                  disabled={rerunLoading[property.gid]}
                >
                  {rerunLoading[property.gid] ? 'Re-running...' : 'Re-run Analysis'}
                </Button>
              </CardContent>
            </Card>
          </Box>
        ))}
      </Box>
    </Container>
  )
}
