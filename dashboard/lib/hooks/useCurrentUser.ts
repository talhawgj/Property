"use client"

import { useState, useEffect } from 'react'
import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'

export interface CurrentUser {
  userId: string
  email?: string
  username?: string
  role?: string
}

/**
 * Hook to get the current authenticated user's information
 * @returns Current user info or null if not authenticated
 */
export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    async function loadUser() {
      try {
        setLoading(true)
        setError(null)

        const [session, currentUser] = await Promise.all([
          fetchAuthSession(),
          getCurrentUser()
        ])

        const userId = session?.tokens?.idToken?.payload?.sub as string
        const email = session?.tokens?.idToken?.payload?.email as string
        const role = session?.tokens?.idToken?.payload?.['custom:role'] as string

        if (userId) {
          setUser({
            userId,
            email,
            username: currentUser.username,
            role
          })
        } else {
          setUser(null)
        }
      } catch (err) {
        console.error('Failed to load user:', err)
        setError(err as Error)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    loadUser()
  }, [])

  return { user, loading, error }
}

/**
 * Get the current user's ID (async)
 * @returns User ID or null if not authenticated
 */
export async function getUserId(): Promise<string | null> {
  try {
    const session = await fetchAuthSession()
    return (session?.tokens?.idToken?.payload?.sub as string) || null
  } catch (error) {
    console.error('Failed to get user ID:', error)
    return null
  }
}
