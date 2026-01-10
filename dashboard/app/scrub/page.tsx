"use client"

import { ScrubData } from "@/components/analysis/scrub-data"

export default function ScrubPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Data Scrub</h1>
        <p className="text-muted-foreground">
          Upload and process CSV/XLSX files, then batch them for analysis
        </p>
      </div>

      <ScrubData />
    </div>
  )
}