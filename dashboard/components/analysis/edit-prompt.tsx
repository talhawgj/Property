"use client"

import React, { useState, useEffect } from "react"
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  Paper,
  CircularProgress,
  Container,
  Stack,
  Divider
} from "@mui/material"
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon
} from "@mui/icons-material"
import api from "@/lib/api"
import { noSSR } from "next/dynamic"

interface CustomField {
  key: string
  value: string
}

interface RequiredOutput {
  nol: number
[key: `sentence-${number}`]: string;

  closingRemarks: string
  customFields: CustomField[]

}

interface FormData {
  styleAndOutput: string
  requiredOutput: RequiredOutput
  markdownHandling: string
  generalRules: string
}

export function EditPrompt() {
  const [formData, setFormData] = useState<FormData>({
    styleAndOutput: "",
    requiredOutput: {
      nol: 0,
      closingRemarks: "",
      customFields: []
    },
    markdownHandling: "",
    generalRules: ""
  })
  const [editedData, setEditedData] = useState<FormData>({
    styleAndOutput: "",
    requiredOutput: {
      nol: 0,
      closingRemarks: "",
      customFields: []
    },
    markdownHandling: "",
    generalRules: ""
  })
  const [isEditing, setIsEditing] = useState<boolean>(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isSaving, setIsSaving] = useState<boolean>(false)
  const [isFetching, setIsFetching] = useState<boolean>(false)
  const [error, setError] = useState<string>("")
  const [successMessage, setSuccessMessage] = useState<string>("")

  useEffect(() => {
    loadText()
  }, [])

  const loadText = async (manual = false) => {
    try {
      manual ? setIsFetching(true) : setIsLoading(true)
      setError("")
      setSuccessMessage("")

      // Fetch from Property API
      const response = await api.get("/prompts/prop-insights")
      const data = response.data
      console.log("data")
      const requiredOutput = JSON.parse(data["required_output"])
      console.log(requiredOutput)



      
      // console.log("Fetched data from DynamoDB:", data)
       
      let sentences:Record<string,string> = {}
      const nol = parseInt(requiredOutput.nol) || 0
for (let i = 1; i <= nol; i++) {
    sentences[`sentence-${i}`] = requiredOutput[`sentence-${i}`]
}


      const closingRemarks = requiredOutput["closing-remarks"] || ""
      const requireOutputFields = Object.keys(requiredOutput)

      
      console.log("Parsed NOL:", nol)
      console.log("Parsed closing remarks:", closingRemarks)
      
      const customFields: CustomField[] = []
      Object.keys(data).forEach((key) => {
        if (
          !requireOutputFields.includes(key) &&
          key !== "prompt_id" && 
          key !=="required_output" &&
          key !== "nol" && 
          key !== "closing-remarks" && 
          key !== "style_and_output" && 
          key !== "markdown_handling" && 
          key !== "general_rules" && 
          key !== "updatedAt"
        ) {
          customFields.push({
            key: key,
            value: data[key]
          })
        }
      })
      
      console.log("Custom fields:", customFields)

      const loadedData: FormData = {
        styleAndOutput: data["style_and_output"] || "",
        requiredOutput: {
          nol: nol,
          ...sentences,
          closingRemarks: closingRemarks,
          customFields: customFields
        },
        markdownHandling: data["markdown_handling"] || "",
        generalRules: data["general_rules"] || ""
      }

      setFormData(loadedData)
      setEditedData(JSON.parse(JSON.stringify(loadedData)))
      if (manual) setSuccessMessage("Text content refreshed successfully")
    } catch (e: any) {
      console.error("API error:", e)
      if (e.response?.status === 404) {
        setError("No prompt document found in database. Please create the document 'prop-insight' in the 'prompt' table.")
      } else if (e.response?.status === 401) {
        setError("Authentication error. Please check your API credentials.")
      } else {
        setError("Error loading text: " + (e.response?.data?.detail || e.message || "Unknown error"))
      }
    } finally {
      manual ? setIsFetching(false) : setIsLoading(false)
    }
  }

  const handleFetchText = () => loadText(true)

  const handleEdit = () => {
    setIsEditing(true)
    setError("")
    setSuccessMessage("")
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditedData(JSON.parse(JSON.stringify(formData)))
  }

  const handleAddSentence = () => {
    const newNol = editedData.requiredOutput.nol + 1
    const newKey = `sentence-${newNol}` as keyof RequiredOutput
    
    setEditedData({
      ...editedData,
      requiredOutput: {
        ...editedData.requiredOutput,
        nol: newNol,
        [newKey]: ""
      }
    })
  }

  const handleDeleteSentence = (sentenceIndex: number) => {
    const newRequiredOutput: any = { ...editedData.requiredOutput }
    const newNol = editedData.requiredOutput.nol - 1
    
    // Remove the sentence being deleted and shift all subsequent sentences
    for (let i = sentenceIndex; i <= editedData.requiredOutput.nol; i++) {
      const currentKey = `sentence-${i}`
      const nextKey = `sentence-${i + 1}`
      
      if (i === editedData.requiredOutput.nol) {
        // Delete the last sentence
        delete newRequiredOutput[currentKey]
      } else {
        // Shift the next sentence to current position
        newRequiredOutput[currentKey] = newRequiredOutput[nextKey] || ""
      }
    }
    
    newRequiredOutput.nol = newNol
    setEditedData({
      ...editedData,
      requiredOutput: newRequiredOutput as RequiredOutput
    })
  }

  const handleCustomFieldChange = (index: number, field: 'key' | 'value', value: string) => {
    const updatedFields = [...editedData.requiredOutput.customFields]
    updatedFields[index] = {
      ...updatedFields[index],
      [field]: value
    }
    setEditedData({
      ...editedData,
      requiredOutput: {
        ...editedData.requiredOutput,
        customFields: updatedFields
      }
    })
  }

  const handleConfirm = async () => {
    try {
      setIsSaving(true)
      setError("")
      setSuccessMessage("")

      // Build required_output object with nol, sentences, and closing-remarks
      const requiredOutputData: Record<string, any> = {
        nol: editedData.requiredOutput.nol,
        "closing-remarks": editedData.requiredOutput.closingRemarks
      }

      // Add sentence fields
      for (let i = 1; i <= editedData.requiredOutput.nol; i++) {
        const key = `sentence-${i}` as keyof RequiredOutput
        requiredOutputData[key] = editedData.requiredOutput[key] || ""
      }

      // Prepare the data for PostgreSQL
      const promptData = {
        general_rules: editedData.generalRules,
        markdown_handling: editedData.markdownHandling,
        required_output: requiredOutputData,  // Send as object, not string
        style_and_output: editedData.styleAndOutput
      }

      console.log("Saving prompt data:", promptData)

      // Save via API
      await api.put("/prompts/prop-insights", promptData)

      setFormData(JSON.parse(JSON.stringify(editedData)))
      setIsEditing(false)
      setSuccessMessage("Text updated successfully")
    } catch (e: any) {
      console.error("API save error:", e)
      if (e.response?.status === 401) {
        setError("Authentication error. Please check your API credentials.")
      } else {
        setError("Error saving text: " + (e.response?.data?.detail || e.message || "Unknown error"))
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <Container maxWidth="md">
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="200px"
          flexDirection="column"
          gap={2}
        >
          <CircularProgress />
          <Typography variant="body1" color="text.secondary">
            Loading text content...
          </Typography>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box py={4}>
        <Typography variant="h4" component="h1" gutterBottom color="primary">
          Edit Prompt Configuration
        </Typography>

        <Stack spacing={3}>
          {error && (
            <Alert severity="error" onClose={() => setError("")}>
              {error}
            </Alert>
          )}
          {successMessage && (
            <Alert severity="success" onClose={() => setSuccessMessage("")}>
              {successMessage}
            </Alert>
          )}

          {/* Style and Output Field */}
          <Paper elevation={2}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom color="primary">
                Style and Output
              </Typography>
              {isEditing ? (
                <TextField
                  fullWidth
                  multiline
                  minRows={5}
                  maxRows={10}
                  value={editedData.styleAndOutput}
                  onChange={(e) => setEditedData({
                    ...editedData,
                    styleAndOutput: e.target.value
                  })}
                  placeholder="Enter style and output instructions..."
                  variant="outlined"
                />
              ) : (
                <Box
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "grey.300",
                    fontFamily: "monospace",
                    fontSize: "14px",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    minHeight: "100px"
                  }}
                >
                  {formData.styleAndOutput || (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      No content available
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
          </Paper>

          {/* Required Output Field */}
          <Paper elevation={2}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom color="primary">
                Required Output
              </Typography>
              
              <Stack spacing={2}>
                {/* NOL Field - Read Only */}
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Number of Lines/Sentences (NOL)
                  </Typography>
                  <Box
                    sx={{
                      p: 1.5,
                      backgroundColor: "grey.50",
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "grey.300"
                    }}
                  >
                    <Typography>{isEditing ? editedData.requiredOutput.nol : formData.requiredOutput.nol}</Typography>
                  </Box>
                </Box>

                <Divider />

                {/* Sentence Fields */}
                {(isEditing ? editedData.requiredOutput.nol : formData.requiredOutput.nol) > 0 && (
                  <Box>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="subtitle2">
                        Sentence Definitions
                      </Typography>
                      {isEditing && (
                        <Button
                          size="small"
                          startIcon={<AddIcon />}
                          onClick={handleAddSentence}
                          variant="outlined"
                        >
                          Add Sentence
                        </Button>
                      )}
                    </Box>
                    <Stack spacing={1}>
                      {Array.from({ length: isEditing ? editedData.requiredOutput.nol : formData.requiredOutput.nol }, (_, i) => {
                        const key = `sentence-${i + 1}` as keyof RequiredOutput
                        const value = isEditing 
                          ? (editedData.requiredOutput[key] as string)
                          : (formData.requiredOutput[key] as string)
                        
                        return (
                          <Box key={key}>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                              <Typography variant="caption" color="text.secondary" gutterBottom>
                                {key}
                              </Typography>
                              {isEditing && (
                                <Button
                                  size="small"
                                  color="error"
                                  startIcon={<DeleteIcon />}
                                  onClick={() => handleDeleteSentence(i + 1)}
                                  sx={{ minWidth: 'auto', px: 1 }}
                                >
                                  Delete
                                </Button>
                              )}
                            </Box>
                            {isEditing ? (
                              <TextField
                                fullWidth
                                multiline
                                minRows={2}
                                maxRows={4}
                                value={value || ''}
                                onChange={(e) => setEditedData({
                                  ...editedData,
                                  requiredOutput: {
                                    ...editedData.requiredOutput,
                                    [key]: e.target.value
                                  }
                                })}
                                placeholder={`Enter definition for ${key}...`}
                                variant="outlined"
                                size="small"
                              />
                            ) : (
                              <Box
                                sx={{
                                  p: 1.5,
                                  backgroundColor: "grey.50",
                                  borderRadius: 1,
                                  border: "1px solid",
                                  borderColor: "grey.300",
                                  fontSize: "14px",
                                  whiteSpace: "pre-wrap",
                                  wordBreak: "break-word"
                                }}
                              >
                                {value || (
                                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                                    No definition
                                  </Typography>
                                )}
                              </Box>
                            )}
                          </Box>
                        )
                      })}
                    </Stack>
                  </Box>
                )}

                <Divider />

                {/* Custom Fields based on NOL */}
                {isEditing && editedData.requiredOutput.nol > 0 && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Custom Fields ({editedData.requiredOutput.customFields.length})
                    </Typography>
                    <Stack spacing={2}>
                      {editedData.requiredOutput.customFields.map((field, index) => (
                        <Box key={index} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <Box sx={{ flex: '0 0 40%' }}>
                            <TextField
                              fullWidth
                              label={`Field ${index + 1} Key`}
                              value={field.key}
                              onChange={(e) => handleCustomFieldChange(index, 'key', e.target.value)}
                              variant="outlined"
                              size="small"
                            />
                          </Box>
                          <Box sx={{ flex: '0 0 60%' }}>
                            <TextField
                              fullWidth
                              label={`Field ${index + 1} Value`}
                              value={field.value}
                              onChange={(e) => handleCustomFieldChange(index, 'value', e.target.value)}
                              variant="outlined"
                              size="small"
                              multiline
                              maxRows={3}
                            />
                          </Box>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )}

                {!isEditing && formData.requiredOutput.customFields.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Custom Fields
                    </Typography>
                    <Stack spacing={1}>
                      {formData.requiredOutput.customFields.map((field, index) => (
                        <Box
                          key={index}
                          sx={{
                            p: 2,
                            backgroundColor: "grey.50",
                            borderRadius: 1,
                            border: "1px solid",
                            borderColor: "grey.300"
                          }}
                        >
                          <Typography variant="subtitle2" color="primary">
                            {field.key}
                          </Typography>
                          <Typography variant="body2" sx={{ mt: 0.5 }}>
                            {field.value}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )}

                <Divider />

                {/* Closing Remarks Field */}
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Closing Remarks
                  </Typography>
                  {isEditing ? (
                    <TextField
                      fullWidth
                      multiline
                      minRows={3}
                      maxRows={6}
                      value={editedData.requiredOutput.closingRemarks}
                      onChange={(e) => setEditedData({
                        ...editedData,
                        requiredOutput: {
                          ...editedData.requiredOutput,
                          closingRemarks: e.target.value
                        }
                      })}
                      placeholder="Enter closing remarks..."
                      variant="outlined"
                    />
                  ) : (
                    <Box
                      sx={{
                        p: 2,
                        backgroundColor: "grey.50",
                        borderRadius: 1,
                        border: "1px solid",
                        borderColor: "grey.300",
                        fontFamily: "monospace",
                        fontSize: "14px",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        minHeight: "60px"
                      }}
                    >
                      {formData.requiredOutput.closingRemarks || (
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                          No closing remarks
                        </Typography>
                      )}
                    </Box>
                  )}
                </Box>
              </Stack>
            </Box>
          </Paper>

          {/* Markdown Handling Field */}
          <Paper elevation={2}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom color="primary">
                Markdown Handling
              </Typography>
              {isEditing ? (
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  maxRows={8}
                  value={editedData.markdownHandling}
                  onChange={(e) => setEditedData({
                    ...editedData,
                    markdownHandling: e.target.value
                  })}
                  placeholder="Enter markdown handling rules..."
                  variant="outlined"
                />
              ) : (
                <Box
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "grey.300",
                    fontFamily: "monospace",
                    fontSize: "14px",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    minHeight: "80px"
                  }}
                >
                  {formData.markdownHandling || (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      No content available
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
          </Paper>

          {/* General Rules Field */}
          <Paper elevation={2}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom color="primary">
                General Rules
              </Typography>
              {isEditing ? (
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  maxRows={8}
                  value={editedData.generalRules}
                  onChange={(e) => setEditedData({
                    ...editedData,
                    generalRules: e.target.value
                  })}
                  placeholder="Enter general rules..."
                  variant="outlined"
                />
              ) : (
                <Box
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "grey.300",
                    fontFamily: "monospace",
                    fontSize: "14px",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    minHeight: "80px"
                  }}
                >
                  {formData.generalRules || (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      No content available
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
          </Paper>

          {/* Action Buttons */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            gap={2}
            flexDirection={{ xs: "column", sm: "row" }}
          >
            {isEditing ? (
              <>
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<CancelIcon />}
                  onClick={handleCancel}
                  disabled={isSaving}
                >
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
                  onClick={handleConfirm}
                  disabled={isSaving}
                >
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<EditIcon />}
                  onClick={handleEdit}
                >
                  Edit Configuration
                </Button>
                <Button
                  variant="outlined"
                  color="primary"
                  startIcon={isFetching ? <CircularProgress size={16} /> : <RefreshIcon />}
                  onClick={handleFetchText}
                  disabled={isFetching}
                >
                  {isFetching ? "Refreshing..." : "Refresh"}
                </Button>
              </>
            )}
          </Box>
        </Stack>
      </Box>
    </Container>
  )
}
