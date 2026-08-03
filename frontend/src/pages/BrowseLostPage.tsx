import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage, listPublicLostItems } from '../lib/api'
import type { PublicLostItem } from '../lib/types'

export function BrowseLostPage() {
  const [items, setItems] = useState<PublicLostItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        setItems(await listPublicLostItems())
      } catch (err) {
        setError(getApiErrorMessage(err, 'Unable to load public lost items'))
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [])

  if (loading) {
    return <div className="mx-auto max-w-7xl px-4 py-12 text-slate-300">Loading public lost items…</div>
  }

  if (error) {
    return <div className="mx-auto max-w-7xl px-4 py-12 text-rose-200">{error}</div>
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">
      <section className="panel mb-8">
        <h1 className="text-3xl font-black text-white">Browse Lost Items</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Review open lost-item reports from all users and submit a similar found item when you spot a possible match.
        </p>
      </section>

      {items.length === 0 ? (
        <div className="panel text-center">
          <h2 className="text-xl font-bold text-white">No open lost items</h2>
          <p className="mt-2 text-sm text-slate-400">Check back later when more reports are submitted.</p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <article key={item.id} className="panel flex h-full flex-col gap-4">
              {item.image_url ? (
                <img src={item.image_url} alt={item.item_name} className="h-56 w-full rounded-2xl object-cover" />
              ) : (
                <div className="flex h-56 items-center justify-center rounded-2xl border border-dashed border-white/10 text-slate-500">
                  No image
                </div>
              )}
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-white">{item.item_name}</h2>
                <p className="text-sm text-slate-300"><span className="text-slate-400">Category:</span> {item.category}</p>
                <p className="text-sm text-slate-300"><span className="text-slate-400">Description:</span> {item.description}</p>
                <p className="text-sm text-slate-300"><span className="text-slate-400">Date lost:</span> {item.date_lost}</p>
                <p className="text-sm text-slate-300"><span className="text-slate-400">Location:</span> {item.location}</p>
              </div>
              <div className="mt-auto flex gap-3">
                <Link className="btn-primary w-full text-center" to="/report-found">
                  Report Similar Found Item
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  )
}