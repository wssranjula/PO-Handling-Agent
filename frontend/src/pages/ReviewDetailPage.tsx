import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/PageState'
import { DecisionPanel } from '../review/DecisionPanel'
import { PurchaseOrderEditor } from '../review/PurchaseOrderEditor'
import type { PurchaseOrder, ReviewDetail } from '../types'
import { reasonLabel } from '../utils'

export function ReviewDetailPage() {
  const { reviewId = '' } = useParams()
  const navigate = useNavigate()
  const [review, setReview] = useState<ReviewDetail | null>(null)
  const [order, setOrder] = useState<PurchaseOrder | null>(null)
  const [reviewer, setReviewer] = useState('Operations Reviewer')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.getReview(reviewId)
      .then((data) => {
        setReview(data)
        setOrder(data.enrichment?.resolved_order ?? data.extracted_data?.order ?? null)
      })
      .catch((requestError: Error) => setError(requestError.message))
  }, [reviewId])

  const approve = async () => {
    if (!order || !reviewer.trim()) return
    setSubmitting(true)
    setError('')
    setMessage('')
    try {
      const result = await api.approveReview(reviewId, order, reviewer.trim(), notes)
      if (result.status === 'approved') {
        navigate(`/orders/${result.draft_order_id}`)
        return
      }
      setMessage(`Still needs review: ${result.review_reasons.map(reasonLabel).join(', ')}`)
      const fresh = await api.getReview(reviewId)
      setReview(fresh)
      setOrder(fresh.enrichment?.resolved_order ?? order)
    } catch (requestError) {
      setError((requestError as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const reject = async () => {
    if (!reviewer.trim() || !notes.trim()) {
      setError('Add a rejection reason in the reviewer notes field.')
      return
    }
    if (!window.confirm('Reject this purchase order? This closes the review without creating an order.')) return
    setSubmitting(true)
    setError('')
    try {
      await api.rejectReview(reviewId, reviewer.trim(), notes.trim())
      navigate('/reviews')
    } catch (requestError) {
      setError((requestError as Error).message)
      setSubmitting(false)
    }
  }

  if (error && !review) return <section className="page"><ErrorState message={error} /></section>
  if (!review || !order) return <section className="page"><LoadingState /></section>

  const failures = review.validation_results?.filter((result) => !result.passed) ?? []
  return (
    <section className="page review-detail">
      <Link to="/reviews" className="back-link"><ArrowLeft size={16} /> Human review</Link>
      <div className="detail-title">
        <div>
          <p className="eyebrow amber">Decision required</p>
          <h1>{order.po_number || 'Unidentified purchase order'}</h1>
          <p>Edit the agent’s resolved values, then submit a decision.</p>
        </div>
      </div>
      <div className="review-layout">
        <PurchaseOrderEditor order={order} onChange={setOrder} />
        <DecisionPanel
          review={review}
          failures={failures}
          reviewer={reviewer}
          notes={notes}
          error={error}
          message={message}
          submitting={submitting}
          onReviewerChange={setReviewer}
          onNotesChange={setNotes}
          onApprove={approve}
          onReject={reject}
        />
      </div>
    </section>
  )
}
