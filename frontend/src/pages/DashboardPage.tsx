import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  confirmMatch,
  getApiErrorMessage,
  listFoundItems,
  listLostItems,
  listMatches,
  rejectMatch,
} from '../lib/api'
import type { FoundItem, LostItem, Match } from '../lib/types'
import { MatchBadge } from '../components/MatchBadge'

type Filter = 'pending' | 'resolved'
type TabKey = 'lost' | 'found' | 'matches'

export function DashboardPage() {
  const [lostItems, setLostItems] = useState<LostItem[]>([])
  const [foundItems, setFoundItems] = useState<FoundItem[]>([])
  const [matches, setMatches] = useState<Match[]>([])
  const [tab, setTab] = useState<TabKey>('lost')
  const [filter, setFilter] = useState<Filter>('pending')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setLoading(true)

      const [lost, found, allMatches] = await Promise.all([
        listLostItems(),
        listFoundItems(),
        listMatches(),
      ])

      setLostItems(lost)
      setFoundItems(found)
      setMatches(allMatches)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to load dashboard'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const filteredMatches = useMemo(() => {
    if (filter === 'pending') {
      return matches.filter((match) => match.status === 'pending')
    }

    return matches.filter((match) => match.status !== 'pending')
  }, [matches, filter])

  async function mutateMatch(
    action: 'confirm' | 'reject',
    matchId: number,
  ) {
    const next =
      action === 'confirm'
        ? await confirmMatch(matchId)
        : await rejectMatch(matchId)

    setMatches((current) =>
      current.map((match) =>
        match.id === matchId ? next : match,
      ),
    )
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 text-slate-300">
        Loading dashboard…
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 text-rose-200">
        {error}
      </div>
    )
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">
      <section className="panel mb-8 overflow-hidden">
        <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr] lg:items-center">
          <div>
            <p className="mb-3 inline-flex rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-300">
              AI matching active
            </p>

            <h1 className="text-4xl font-black tracking-tight text-white">
              Track lost items, found items, and AI matches in one place.
            </h1>

            <p className="mt-4 max-w-2xl text-slate-300">
              Use the dashboard to review pending matches, manage confirmed
              items, and add new items when needed.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <Stat label="Lost items" value={lostItems.length} />
            <Stat label="Found items" value={foundItems.length} />
            <Stat label="Matches" value={matches.length} />
          </div>
        </div>
      </section>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <TabButton
          active={tab === 'lost'}
          onClick={() => setTab('lost')}
        >
          My Lost Items
        </TabButton>

        <TabButton
          active={tab === 'found'}
          onClick={() => setTab('found')}
        >
          My Found Items
        </TabButton>

        <TabButton
          active={tab === 'matches'}
          onClick={() => setTab('matches')}
        >
          Matches
        </TabButton>
      </div>

      {tab === 'matches' ? (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <TabButton
              active={filter === 'pending'}
              onClick={() => setFilter('pending')}
            >
              Pending
            </TabButton>

            <TabButton
              active={filter === 'resolved'}
              onClick={() => setFilter('resolved')}
            >
              Resolved
            </TabButton>
          </div>

          {filteredMatches.length === 0 ? (
            <EmptyState
              title="No matches yet"
              subtitle="When the AI finds a likely counterpart, it will appear here."
            />
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            {filteredMatches.map((match) => (
              <article
                key={match.id}
                className="panel space-y-4"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <MatchBadge score={match.final_score} />

                  <span className="badge bg-white/10 text-slate-200">
                    {match.status}
                  </span>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <PreviewCard
                    title={match.lost_item.item_name}
                    subtitle={match.lost_item.location}
                    image={match.lost_item.image_url}
                    description={match.lost_item.description}
                  />

                  <PreviewCard
                    title={match.found_item.category}
                    subtitle={match.found_item.location}
                    image={match.found_item.image_url}
                    description={match.found_item.description}
                  />
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link
                    className="btn-secondary"
                    to={`/matches/${match.id}`}
                  >
                    Open Details
                  </Link>

                  <button
                    className="btn-primary"
                    disabled={match.status !== 'pending'}
                    onClick={() =>
                      void mutateMatch('confirm', match.id)
                    }
                  >
                    Confirm
                  </button>

                  <button
                    className="btn-secondary"
                    disabled={match.status !== 'pending'}
                    onClick={() =>
                      void mutateMatch('reject', match.id)
                    }
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {tab === 'lost' ? (
        <ListPanel
          title="My Lost Items"
          emptyTitle="No lost items yet"
          emptySubtitle="Add your first lost item to start the matching process."
          actionHref="/report-lost"
          actionLabel="Add Lost Item"
          items={lostItems.map((item) => (
            <PreviewCard
              key={item.id}
              title={item.item_name}
              subtitle={`${item.category} • ${item.location}`}
              image={item.image_url}
              description={item.description}
            />
          ))}
        />
      ) : null}

      {tab === 'found' ? (
        <ListPanel
          title="My Found Items"
          emptyTitle="No found items yet"
          emptySubtitle="Add a found item if you discovered something on campus."
          actionHref="/report-found"
          actionLabel="Add Found Item"
          items={foundItems.map((item) => (
            <PreviewCard
              key={item.id}
              title={item.category}
              subtitle={`${item.location} • ${item.status}`}
              image={item.image_url}
              description={item.description}
            />
          ))}
        />
      ) : null}
    </main>
  )
}

function Stat({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-black text-white">
        {value}
      </p>
    </div>
  )
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      className={active ? 'btn-primary' : 'btn-secondary'}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  )
}

function EmptyState({
  title,
  subtitle,
}: {
  title: string
  subtitle: string
}) {
  return (
    <div className="panel text-center">
      <h3 className="text-lg font-bold text-white">
        {title}
      </h3>

      <p className="mt-2 text-sm text-slate-400">
        {subtitle}
      </p>
    </div>
  )
}

function PreviewCard({
  title,
  subtitle,
  image,
  description,
}: {
  title: string
  subtitle: string
  image?: string | null
  description: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
      {image ? (
        <img
          src={image}
          alt={title}
          className="mb-4 h-40 w-full rounded-xl object-cover"
        />
      ) : (
        <div className="mb-4 flex h-40 items-center justify-center rounded-xl border border-dashed border-white/10 text-slate-500">
          No image
        </div>
      )}

      <p className="font-semibold text-white">
        {title}
      </p>

      <p className="mt-1 text-sm text-slate-400">
        {subtitle}
      </p>

      <p className="mt-3 line-clamp-4 text-sm text-slate-300">
        {description}
      </p>
    </div>
  )
}

function ListPanel({
  title,
  emptyTitle,
  emptySubtitle,
  actionHref,
  actionLabel,
  items,
}: {
  title: string
  emptyTitle: string
  emptySubtitle: string
  actionHref: string
  actionLabel: string
  items: ReactNode[]
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-white">
          {title}
        </h2>

        <Link
          className="btn-primary"
          to={actionHref}
        >
          {actionLabel}
        </Link>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title={emptyTitle}
          subtitle={emptySubtitle}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items}
        </div>
      )}
    </section>
  )
}