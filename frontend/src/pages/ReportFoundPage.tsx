import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createFoundItem } from '../lib/api'
import { ReportForm } from '../components/ReportForm'

export function ReportFoundPage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(formData: FormData) {
    setSubmitting(true)
    try {
      await createFoundItem(formData)
      navigate('/dashboard')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 lg:px-8">
      <ReportForm mode="found" onSubmit={handleSubmit} submitting={submitting} />
    </main>
  )
}
