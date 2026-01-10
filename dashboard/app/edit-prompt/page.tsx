"use client"

import { EditPrompt } from "@/components/analysis/edit-prompt"

export default function EditPromptPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Edit AI Prompt</h1>
        <p className="text-muted-foreground">
          Configure AI prompt templates for property descriptions
        </p>
      </div>

      <EditPrompt />
    </div>
  )
}
