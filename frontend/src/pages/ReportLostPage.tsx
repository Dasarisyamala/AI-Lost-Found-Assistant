import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createLostItem } from '../lib/api'
import { ReportForm } from '../components/ReportForm'

export function ReportLostPage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(formData: FormData) {
    setSubmitting(true)
    try {
      await createLostItem(formData)
      navigate('/dashboard')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 lg:px-8">
      <ReportForm mode="lost" onSubmit={handleSubmit} submitting={submitting} />
    </main>
  )
}
