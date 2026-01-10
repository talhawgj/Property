import axios from "axios"
import { fetchAuthSession } from 'aws-amplify/auth'


const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_PROPERTY_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://10.8.0.1:8001",
})

// Add x-api-key and x-user-id headers to every request
api.interceptors.request.use(async (config) => {
  // Add API key
  const apiKey = process.env.NEXT_PUBLIC_GIS_API_KEY || process.env.NEXT_PUBLIC_RADCORP_API_KEY
  if (apiKey) {
    config.headers["x-api-key"] = apiKey
  }

  // Add user ID from Amplify session
  try {
    const session = await fetchAuthSession()
    const userId = session?.tokens?.idToken?.payload?.sub
    if (userId) {
      config.headers["x-user-id"] = userId as string
    }
  } catch (error) {
    // User not authenticated, continue without x-user-id
    console.warn("No authenticated user session:", error)
  }

  return config
})

export default api
