import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { confirmMatch, getApiErrorMessage, getMatch, rejectMatch } from '../lib/api'
import type { Match } from '../lib/types'
import { MatchBadge } from '../components/MatchBadge'

export function MatchDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [match, setMatch] = useState<Match | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      if (!id) return
      try {
        setLoading(true)
        setMatch(await getMatch(Number(id)))
      } catch (err) {
        setError(getApiErrorMessage(err, 'Unable to load match'))
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [id])

  async function handleAction(action: 'confirm' | 'reject') {
    if (!id) return
    setSaving(true)
    try {
      const next = action === 'confirm' ? await confirmMatch(Number(id)) : await rejectMatch(Number(id))
      setMatch(next)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-5xl px-4 py-12 text-slate-300">Loading match…</div>
  }

  if (error) {
    return <div className="mx-auto max-w-5xl px-4 py-12 text-rose-200">{error}</div>
  }

  if (!match) {
    return <div className="mx-auto max-w-5xl px-4 py-12 text-slate-300">Match not found.</div>
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Match #{match.id}</h1>
          <p className="mt-2 text-sm text-slate-400">Compare the lost and found reports, then confirm or reject the match.</p>
        </div>
        <Link to="/dashboard" className="btn-secondary">Back to dashboard</Link>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <MatchBadge score={match.final_score} />
        <span className="badge bg-white/10 text-slate-200">Status: {match.status}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Lost item" item={match.lost_item} image={match.lost_item.image_url} />
        <Card title="Found item" item={match.found_item} image={match.found_item.image_url} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button className="btn-primary" disabled={saving || match.status !== 'pending'} onClick={() => void handleAction('confirm')}>
          Confirm match
        </button>
        <button className="btn-secondary" disabled={saving || match.status !== 'pending'} onClick={() => void handleAction('reject')}>
          Reject match
        </button>
      </div>
    </main>
  )
}

function Card({ title, item, image }: { title: string; item: { item_name?: string; category: string; location: string; description: string }; image?: string | null }) {
  return (
    <section className="panel space-y-4">
      <h2 className="text-xl font-bold text-white">{title}</h2>
      {image ? <img src={image} alt={title} className="h-64 w-full rounded-2xl object-cover" /> : <div className="flex h-64 items-center justify-center rounded-2xl border border-dashed border-white/10 text-slate-500">No image</div>}
      <div className="space-y-2 text-sm text-slate-300">
        {item.item_name ? <p><span className="text-slate-400">Name:</span> {item.item_name}</p> : null}
        <p><span className="text-slate-400">Category:</span> {item.category}</p>
        <p><span className="text-slate-400">Location:</span> {item.location}</p>
        <p><span className="text-slate-400">Description:</span> {item.description}</p>
      </div>
    </section>
  )
}
