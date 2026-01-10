"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Home, MapPin, FileText, User as UserIcon } from "lucide-react"
import { getCurrentUserInfo } from "@/lib/auth/roles"
import { SignOutButton } from "@/components/auth/sign-out-button"

export default function UserDashboardPage() {
  const [userInfo, setUserInfo] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUserInfo() {
      const info = await getCurrentUserInfo()
      setUserInfo(info)
      setLoading(false)
    }
    loadUserInfo()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Loading your dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground">My Dashboard</h1>
              <p className="text-sm text-muted-foreground">Welcome back, {userInfo?.email}</p>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="gap-2">
                <UserIcon className="w-3 h-3" />
                User
              </Badge>
              <SignOutButton />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Welcome Card */}
          <Card className="p-6 col-span-full">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <Home className="w-6 h-6 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-foreground mb-2">
                  Welcome to Your Dashboard
                </h2>
                <p className="text-muted-foreground">
                  This is your personal space to view your properties and related information.
                </p>
              </div>
            </div>
          </Card>

          {/* My Properties */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-500/10 rounded">
                <MapPin className="w-5 h-5 text-blue-500" />
              </div>
              <h3 className="font-semibold text-foreground">My Properties</h3>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold text-foreground">0</div>
              <p className="text-sm text-muted-foreground">
                Properties in your account
              </p>
            </div>
          </Card>

          {/* Documents */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-500/10 rounded">
                <FileText className="w-5 h-5 text-green-500" />
              </div>
              <h3 className="font-semibold text-foreground">Documents</h3>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold text-foreground">0</div>
              <p className="text-sm text-muted-foreground">
                Documents available
              </p>
            </div>
          </Card>

          {/* Account Info */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-500/10 rounded">
                <UserIcon className="w-5 h-5 text-purple-500" />
              </div>
              <h3 className="font-semibold text-foreground">Account</h3>
            </div>
            <div className="space-y-2">
              <div className="text-sm">
                <span className="text-muted-foreground">Email: </span>
                <span className="text-foreground">{userInfo?.email}</span>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Role: </span>
                <span className="text-foreground capitalize">{userInfo?.role}</span>
              </div>
            </div>
          </Card>

          {/* Recent Activity */}
          <Card className="p-6 col-span-full">
            <h3 className="font-semibold text-foreground mb-4">Recent Activity</h3>
            <div className="text-center py-8 text-muted-foreground">
              No recent activity to display
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
