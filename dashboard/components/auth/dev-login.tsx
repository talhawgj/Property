"use client"

import { useState } from "react"
import { Shield, Mail, Lock, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

interface DevLoginProps {
  onLogin: () => void
}

export function DevLogin({ onLogin }: DevLoginProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    const devEmail = process.env.NEXT_PUBLIC_DEV_EMAIL || "arslantar360@gmail.com"
    const devPassword = process.env.NEXT_PUBLIC_DEV_PASSWORD || "uzairdev22"

    if (email === devEmail && password === devPassword) {
      // Store auth state
      localStorage.setItem("dev_auth", "true")
      localStorage.setItem("dev_user", JSON.stringify({
        email: email,
        name: "Dev Admin",
        role: "admin"
      }))
      onLogin()
    } else {
      setError("Invalid credentials. Check your email and password.")
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-card border-border p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">GIS Admin Portal</h1>
          <p className="text-muted-foreground text-sm">Development Mode</p>
          <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-yellow-500/10 border border-yellow-500/20 rounded-full">
            <AlertCircle className="w-3 h-3 text-yellow-500" />
            <span className="text-xs text-yellow-500">DEV MODE ACTIVE</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-muted-foreground mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-input border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:border-ring focus:ring-1 focus:ring-ring"
                placeholder="Enter your email"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-muted-foreground mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-input border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:border-ring focus:ring-1 focus:ring-ring"
                placeholder="Enter your password"
                required
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3 text-base font-medium"
          >
            Sign In
          </Button>
        </form>

        <div className="mt-6 pt-6 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">
            Development mode is active. Use dev credentials to login.
          </p>
          <p className="text-xs text-muted-foreground text-center mt-1">
            Set NEXT_PUBLIC_MODE=production to use AWS Amplify
          </p>
        </div>
      </Card>
    </div>
  )
}
