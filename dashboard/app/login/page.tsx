"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { LoginPage } from "@/components/auth/login-page"
import { DevLogin } from "@/components/auth/dev-login"
import { getCurrentUser } from "aws-amplify/auth"
import { getUserRole } from "@/lib/auth/roles"

export default function Login() {
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const mode = process.env.NEXT_PUBLIC_MODE || "production"

  // Check if already authenticated
  useEffect(() => {
    async function checkAuth() {
      if (mode === "dev") {
        const devAuth = localStorage.getItem("dev_auth")
        if (devAuth === "true") {
          router.push('/')
          return
        }
      } else {
        try {
          await getCurrentUser()
          const role = await getUserRole()
          if (role === 'user') {
            router.push('/user-dashboard')
          } else {
            router.push('/')
          }
          return
        } catch {
          // Not authenticated, stay on login page
        }
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [mode, router])

  const handleDevLogin = () => {
    localStorage.setItem("dev_auth", "true")
    router.push('/')
  }

  const handleAmplifyLoginSuccess = async () => {
    // This component is rendered as children of Authenticator when logged in
    // So we just need to redirect
    try {
        const role = await getUserRole()
        if (role === 'user') {
            router.push('/user-dashboard')
        } else {
            router.push('/')
        }
    } catch (e) {
        console.error("Error fetching role:", e)
        router.push('/')
    }
    return null
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Loading...</div>
      </div>
    )
  }

  if (mode === "dev") {
    return <DevLogin onLogin={handleDevLogin} />
  }

  return (
    <LoginPage>
      <AuthRedirect />
    </LoginPage>
  )
}

function AuthRedirect() {
    const router = useRouter()
    
    useEffect(() => {
       async function redirect() {
         try {
             // We can check role here too or just trust the earlier check/default
             const role = await getUserRole()
             if (role === 'user') {
                 router.push('/user-dashboard')
             } else {
                 router.push('/')
             }
         } catch {
             router.push('/')
         }
       }
       redirect()
    }, [router])
    
    return (
        <div className="min-h-screen bg-background flex items-center justify-center">
            <div className="text-foreground">Redirecting...</div>
        </div>
    )
}
