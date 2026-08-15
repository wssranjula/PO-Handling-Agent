import { ArrowRight, CircleAlert, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { EmptyState, ErrorState, LoadingState } from '../components/PageState'
import { StatusBadge } from '../components/StatusBadge'
import type { ReviewSummary } from '../types'
import { reasonLabel, shortDate } from '../utils'

export function ReviewsPage() {
  const [reviews, setReviews] = useState<ReviewSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => {
    setLoading(true)
    setError('')
    api.listReviews().then(setReviews).catch((err: Error) => setError(err.message)).finally(() => setLoading(false))
  }
  useEffect(() => {
    let active = true
    api.listReviews()
      .then((result) => { if (active) setReviews(result) })
      .catch((err: Error) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  return (
    <section className="page">
      <div className="page-heading">
        <div><p className="eyebrow amber">Exception queue</p><h1>Human review</h1><p>Resolve uncertain or policy-breaking purchase orders before they move forward.</p></div>
        <button className="button secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </div>
      {!loading && !error && reviews.length > 0 && <div className="attention-banner"><CircleAlert /><div><strong>{reviews.length} {reviews.length === 1 ? 'order needs' : 'orders need'} attention</strong><span>Review the evidence, correct any fields, then approve or reject.</span></div></div>}
      {loading ? <LoadingState /> : error ? <ErrorState message={error} /> : reviews.length === 0 ? (
        <EmptyState title="The review queue is clear" detail="New exceptions will appear here when the agent needs a human decision." />
      ) : <div className="review-grid">{reviews.map((review) => (
        <Link to={`/reviews/${review.id}`} className="review-card" key={review.id}>
          <div className="review-card-top"><StatusBadge status={review.status} /><span>{shortDate(review.created_at)}</span></div>
          <h2>Review purchase order</h2>
          <p className="run-id">Run {review.run_id.slice(0, 8)}</p>
          <div className="reason-list">{review.reasons.slice(0, 3).map((reason) => <span key={reason}>{reasonLabel(reason)}</span>)}</div>
          <div className="review-card-action">Open review <ArrowRight size={16} /></div>
        </Link>
      ))}</div>}
    </section>
  )
}
