export function MatchBadge({ score }: { score: number }) {
  const label = score >= 0.85 ? 'High' : score >= 0.75 ? 'Medium' : 'Low'
  const classes = score >= 0.85 ? 'bg-emerald-500/15 text-emerald-300' : score >= 0.75 ? 'bg-amber-500/15 text-amber-300' : 'bg-rose-500/15 text-rose-300'
  return <span className={`badge ${classes}`}>{label} confidence {(score * 100).toFixed(0)}%</span>
}
