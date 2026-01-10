"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { ChevronRight, Monitor, Settings, Shield, Target, Users, Database, BarChart3, FileText, Layers, FileSpreadsheet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SignOutButton } from "@/components/auth/sign-out-button"
import { useAnalysis } from "@/contexts/analysis-context"
import AdminDashboard from "@/app/dashboard/page"
import CommandCenterPage from "./command-center/page"
import AgentNetworkPage from "./agent-network/page"
import OperationsPage from "./operations/page"
import IntelligencePage from "./intelligence/page"
import SystemsPage from "./systems/page"
import AnalysisPage from "./analysis/page"
import BatchAnalysisPage from "./batch-analysis/page"
import EditPromptPage from "./edit-prompt/page"
import LogsPage from "./logs/page"
import ScrubPage from "./scrub/page"
import { getCurrentUser } from "aws-amplify/auth"
import { getUserRole, type UserRole } from "@/lib/auth/roles"

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [userRole, setUserRole] = useState<UserRole | null>(null)
  const [activeSection, setActiveSection] = useState("dashboard")
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const router = useRouter()
  const mode = process.env.NEXT_PUBLIC_MODE || "production"

  useEffect(() => {
    async function checkAuth() {
      if (mode === "dev") {
        // Dev mode - check localStorage
        const devAuth = localStorage.getItem("dev_auth")
        const isAuth = devAuth === "true"
        
        if (isAuth) {
          setIsAuthenticated(true)
          // In dev mode, default to admin role
          setUserRole('admin')
        } else {
          setIsAuthenticated(false)
          router.push('/login')
        }
      } else {
        // Production mode - check Amplify auth
        try {
          await getCurrentUser()
          setIsAuthenticated(true)
          
          // Get user role
          const role = await getUserRole()
          setUserRole(role)
          
          // Redirect users based on role
          if (role === 'user') {
            router.push('/user-dashboard')
            return
          }
        } catch {
          setIsAuthenticated(false)
          setUserRole(null)
          router.push('/login')
        }
      }
      setIsLoading(false)
    }
    checkAuth()

    // Set up an interval to check auth state periodically
    const interval = setInterval(checkAuth, 300000)
    
    // Clean up interval on unmount
    return () => clearInterval(interval)
  }, [mode, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Loading...</div>
      </div>
    )
  }

  // Not authenticated - show empty (redirecting)
  if (!isAuthenticated) {
    return null
  }

  // Authenticated - show main layout
  return (
    <MainLayout 
      activeSection={activeSection}
      setActiveSection={setActiveSection}
      sidebarCollapsed={sidebarCollapsed}
      setSidebarCollapsed={setSidebarCollapsed}
    />
  )
}

function MainLayout({ 
  activeSection, 
  setActiveSection, 
  sidebarCollapsed, 
  setSidebarCollapsed 
}: {
  activeSection: string
  setActiveSection: (section: string) => void
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
}) {
  const { setNavigateToSection } = useAnalysis()

  // Register navigation function on mount
  useEffect(() => {
    setNavigateToSection(() => setActiveSection)
  }, [setActiveSection, setNavigateToSection])

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <div
        className={`${sidebarCollapsed ? "w-16" : "w-64"} bg-sidebar border-r border-border transition-all duration-300 fixed md:relative z-50 md:z-auto h-full`}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-8">
            <div className={`${sidebarCollapsed ? "hidden" : "block"}`}>
              <h1 className="text-primary font-bold text-lg tracking-wider">GIS ADMIN</h1>
              <p className="text-muted-foreground text-xs">v2.0 PORTAL</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-muted-foreground hover:text-primary"
            >
              <ChevronRight
                className={`w-4 h-4 sm:w-5 sm:h-5 transition-transform ${sidebarCollapsed ? "" : "rotate-180"}`}
              />
            </Button>
          </div>

          <nav className="space-y-2">
            {[
              { id: "dashboard", icon: Database, label: "DASHBOARD" },
              { id: "agents", icon: Users, label: "PROPERTY CATALOGUE" },
              { id: "batch-analysis", icon: Layers, label: "BATCH ANALYSIS" },
              { id: "scrub", icon: FileSpreadsheet, label: "SCRUB" },
              { id: "edit-prompt", icon: FileText, label: "EDIT PROMPT" },
              { id: "logs", icon: FileText, label: "LOGS" },
              { id: "operations", icon: Target, label: "OPERATIONS" },
              { id: "systems", icon: Settings, label: "SYSTEMS" },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-3 p-3 rounded transition-colors ${
                  activeSection === item.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                <item.icon className="w-5 h-5" />
                {!sidebarCollapsed && <span className="text-sm font-medium">{item.label}</span>}
              </button>
            ))}
          </nav>

          {/* {!sidebarCollapsed && (
            <div className="mt-8 p-4 bg-card border border-border rounded">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                <span className="text-xs text-foreground">SYSTEM ONLINE</span>
              </div>
              <div className="text-xs text-muted-foreground">
                <div>UPTIME: 72:14:33</div>
                <div>USERS: 847 ACTIVE</div>
                <div>PARCELS: 12,847</div>
              </div>
            </div>
          )} */}
        </div>
      </div>

      {/* Mobile Overlay */}
      {!sidebarCollapsed && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setSidebarCollapsed(true)} />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Toolbar */}
        <div className="h-16 bg-background border-b border-border flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <div className="text-sm text-muted-foreground">
              GIS ADMIN / <span className="text-primary">{activeSection.toUpperCase()}</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-xs text-muted-foreground">LAST UPDATE: {new Date().toLocaleString()}</div>
            <SignOutButton />
          </div>
        </div>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-auto">
          {activeSection === "dashboard" && <AdminDashboard setActiveSection={setActiveSection} />}
          {activeSection === "overview" && <CommandCenterPage />}
          {activeSection === "agents" && <AgentNetworkPage />}
          {activeSection === "analysis" && <AnalysisPage />}
          {activeSection === "batch-analysis" && <BatchAnalysisPage />}
          {activeSection === "scrub" && <ScrubPage />}
          {activeSection === "edit-prompt" && <EditPromptPage />}
          {activeSection === "logs" && <LogsPage />}
          {activeSection === "operations" && <OperationsPage />}
          {activeSection === "intelligence" && <IntelligencePage />}
          {activeSection === "systems" && <SystemsPage />}
        </div>
      </div>
    </div>
  )
}
