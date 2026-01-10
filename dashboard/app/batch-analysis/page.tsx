"use client"

import { BatchAnalysis } from "@/components/analysis/batch-analysis"

export default function BatchAnalysisPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Batch Analysis</h1>
        <p className="text-muted-foreground">
          Process multiple properties in batch operations
        </p>
      </div>

      <BatchAnalysis />
    </div>
  )
}
