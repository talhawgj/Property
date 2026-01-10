"use client"

import { Authenticator, ThemeProvider, Theme } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import { Shield, Database, Map, BarChart3 } from 'lucide-react'

const authTheme: Theme = {
  name: 'admin-theme',
  tokens: {
    colors: {
      brand: {
        primary: {
          10: '#f5f5f5',
          20: '#e5e5e5',
          40: '#d4d4d4',
          60: '#a3a3a3',
          80: '#525252',
          90: '#262626',
          100: '#171717',
        },
      },
      background: {
        primary: '#fafafa',
        secondary: '#f5f5f5',
      },
      font: {
        primary: '#171717',
        secondary: '#737373',
      },
    },
    radii: {
      small: '0.375rem',
      medium: '0.5rem',
      large: '0.75rem',
    },
  },
}

export function LoginPage({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Shield className="w-12 h-12 text-primary mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-foreground mb-2">GIS Admin Portal</h1>
          <p className="text-muted-foreground">Sign in to manage your GIS operations</p>
        </div>

        <ThemeProvider theme={authTheme}>
          <Authenticator
            loginMechanisms={['email']}
            signUpAttributes={['email']}
          >
            {children}
          </Authenticator>
        </ThemeProvider>
      </div>
    </div>
  )
}
