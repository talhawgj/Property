"use client"

import { Amplify } from 'aws-amplify'
import { CookieStorage } from 'aws-amplify/utils'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'
import { amplifyConfig } from '@/lib/config/amplify'

// Configure cookie storage for non-HTTPS development
const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || 
   window.location.hostname === '127.0.0.1' ||
   window.location.protocol === 'http:')

// Configure Amplify once at module level for Gen 2
Amplify.configure(amplifyConfig, { ssr: true })

// Set up cookie storage with secure: false for HTTP development
if (isLocalhost) {
  cognitoUserPoolsTokenProvider.setKeyValueStorage(
    new CookieStorage({ 
      domain: typeof window !== 'undefined' ? window.location.hostname : 'localhost',
      secure: false,
      sameSite: 'lax',
      path: '/'
    })
  )
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
