"use client"

import { Suspense } from "react"
import { SingleAnalysis } from "@/components/analysis/single-analysis"

export default function AnalysisPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Property Analysis</h1>
        <p className="text-muted-foreground">
          Analyze individual properties with AI-powered insights
        </p>
      </div>

      <Suspense fallback={<div>Loading...</div>}>
        <SingleAnalysis />
      </Suspense>
    </div>
  )
}
