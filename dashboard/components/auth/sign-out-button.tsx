"use client"

import { LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { signOut } from "aws-amplify/auth"

export function SignOutButton() {
  const router = useRouter()
  const mode = process.env.NEXT_PUBLIC_MODE || "production"

  const handleSignOut = async () => {
    try {
      if (mode === "dev") {
        // Clear dev auth
        localStorage.removeItem("dev_auth")
        localStorage.removeItem("dev_user")
      } else {
        // AWS Amplify sign out
        await signOut()
      }
      // Force full page reload to clear all state
      window.location.href = "/"
    } catch (error) {
      console.error("Error signing out:", error)
      // Force redirect even if there's an error
      window.location.href = "/"
    }
  }

  return (
    <Button
      onClick={handleSignOut}
      variant="ghost"
      size="sm"
      className="text-neutral-400 hover:text-white"
    >
      <LogOut className="w-4 h-4 mr-2" />
      Sign Out
    </Button>
  )
}
