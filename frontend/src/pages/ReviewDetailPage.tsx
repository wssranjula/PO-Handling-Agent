import { ArrowLeft, Check, CircleAlert, Database, Save, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/PageState'
import type { PurchaseOrder, ReviewDetail } from '../types'
import { money, reasonLabel } from '../utils'

type FieldProps = { label: string; value: string | number | null; type?: string; readOnly?: boolean; onChange: (value: string) => void }
function Field({ label, value, type = 'text', readOnly = false, onChange }: FieldProps) {
  return <label className={`field ${readOnly ? 'derived-field' : ''}`}><span>{label}</span><input type={type} readOnly={readOnly} value={value ?? ''} onChange={(event) => onChange(event.target.value)} /></label>
}

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
    api.getReview(reviewId).then((data) => {
      setReview(data)
      setOrder(data.enrichment?.resolved_order ?? data.extracted_data?.order ?? null)
    }).catch((err: Error) => setError(err.message))
  }, [reviewId])

  const update = <K extends keyof PurchaseOrder>(key: K, value: PurchaseOrder[K]) => setOrder((current) => {
    if (!current) return current
    const updated = { ...current, [key]: value }
    if (key === 'tax') {
      updated.total = (Number(updated.subtotal ?? 0) + Number(value ?? 0)).toFixed(2)
    }
    return updated
  })
  const updateLine = (index: number, key: string, value: string) => setOrder((current) => {
    if (!current) return current
    const lineItems = current.line_items.map((line, position) => {
      if (position !== index) return line
      const updatedLine = { ...line, [key]: value || null }
      if (key === 'raw_sku') updatedLine.resolved_sku = null
      if (key === 'quantity' || key === 'unit_price') {
        const quantity = Number(updatedLine.quantity)
        const unitPrice = Number(updatedLine.unit_price)
        const hasValues = updatedLine.quantity !== null && updatedLine.unit_price !== null
        updatedLine.line_total = hasValues && Number.isFinite(quantity) && Number.isFinite(unitPrice)
          ? (quantity * unitPrice).toFixed(2) : null
      }
      return updatedLine
    })
    const subtotal = lineItems.reduce((sum, line) => sum + Number(line.line_total ?? 0), 0)
    return {
      ...current,
      line_items: lineItems,
      subtotal: subtotal.toFixed(2),
      total: (subtotal + Number(current.tax ?? 0)).toFixed(2),
    }
  })

  const approve = async () => {
    if (!order || !reviewer.trim()) return
    setSubmitting(true); setError(''); setMessage('')
    try {
      const result = await api.approveReview(reviewId, order, reviewer.trim(), notes)
      if (result.status === 'approved') navigate(`/orders/${result.draft_order_id}`)
      else {
        setMessage(`Still needs review: ${result.review_reasons.map(reasonLabel).join(', ')}`)
        const fresh = await api.getReview(reviewId); setReview(fresh); setOrder(fresh.enrichment?.resolved_order ?? order)
      }
    } catch (err) { setError((err as Error).message) } finally { setSubmitting(false) }
  }

  const reject = async () => {
    if (!reviewer.trim() || !notes.trim()) { setError('Add a rejection reason in the reviewer notes field.'); return }
    if (!window.confirm('Reject this purchase order? This closes the review without creating an order.')) return
    setSubmitting(true); setError('')
    try { await api.rejectReview(reviewId, reviewer.trim(), notes.trim()); navigate('/reviews') }
    catch (err) { setError((err as Error).message); setSubmitting(false) }
  }

  if (error && !review) return <section className="page"><ErrorState message={error} /></section>
  if (!review || !order) return <section className="page"><LoadingState /></section>
  const failures = review.validation_results?.filter((result) => !result.passed) ?? []

  return <section className="page review-detail">
    <Link to="/reviews" className="back-link"><ArrowLeft size={16} /> Human review</Link>
    <div className="detail-title"><div><p className="eyebrow amber">Decision required</p><h1>{order.po_number || 'Unidentified purchase order'}</h1><p>Edit the agent’s resolved values, then submit a decision.</p></div></div>
    <div className="review-layout">
      <div className="review-form">
        <div className="panel">
          <div className="panel-heading"><h2>Purchase order</h2><span className="edited-hint"><Save size={14} /> Changes are submitted on approval</span></div>
          <div className="form-grid">
            <Field label="PO number" value={order.po_number} onChange={(value) => update('po_number', value)} />
            <Field label="Issue date" type="date" value={order.issue_date} onChange={(value) => update('issue_date', value || null)} />
            <Field label="Customer" value={order.customer_name} onChange={(value) => update('customer_name', value)} />
            <Field label="Currency" value={order.currency} onChange={(value) => update('currency', value.toUpperCase())} />
            <label className="field full"><span>Shipping address</span><textarea value={order.shipping_address ?? ''} onChange={(event) => update('shipping_address', event.target.value)} /></label>
            <Field label="Requested delivery" type="date" value={order.requested_delivery_date} onChange={(value) => update('requested_delivery_date', value || null)} />
            <Field label="Payment terms" value={order.payment_terms} onChange={(value) => update('payment_terms', value)} />
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading"><h2>Line items</h2><span>{order.line_items.length} lines</span></div>
          <div className="editable-lines">{order.line_items.map((line, index) => <div className="editable-line" key={line.line_number}>
            <span className="line-number">{line.line_number}</span>
            <Field label="SKU" value={line.resolved_sku ?? line.raw_sku} onChange={(value) => updateLine(index, 'raw_sku', value)} />
            <Field label="Description" value={line.raw_description} onChange={(value) => updateLine(index, 'raw_description', value)} />
            <Field label="Quantity" type="number" value={line.quantity} onChange={(value) => updateLine(index, 'quantity', value)} />
            <Field label="Unit price" type="number" value={line.unit_price} onChange={(value) => updateLine(index, 'unit_price', value)} />
            <Field label="Line total" type="number" readOnly value={line.line_total} onChange={() => undefined} />
          </div>)}</div>
          <div className="form-grid totals-form">
            <Field label="Subtotal" type="number" readOnly value={order.subtotal} onChange={() => undefined} />
            <Field label="Tax" type="number" value={order.tax} onChange={(value) => update('tax', value)} />
            <Field label="Total" type="number" readOnly value={order.total} onChange={() => undefined} />
          </div>
        </div>
      </div>
      <aside className="decision-panel">
        <div className="panel sticky">
          <h2>Why it was flagged</h2>
          <div className="failure-list">{failures.length ? failures.map((failure) => <div key={failure.code}><CircleAlert size={17} /><span><strong>{reasonLabel(failure.code)}</strong><small>{failure.message}</small></span></div>) : review.reasons.map((reason) => <div key={reason}><CircleAlert size={17} /><strong>{reasonLabel(reason)}</strong></div>)}</div>
          {review.enrichment?.matches.length ? <div className="rag-evidence"><p><Database size={15} /> RAG evidence</p>{review.enrichment.matches.slice(0, 4).map((match, index) => <div key={`${match.source_title}-${index}`}><strong>{match.entity_name ?? match.source_title}</strong><span>{Math.round(match.similarity * 100)}% match · {match.source_title}</span></div>)}</div> : null}
          <div className="decision-fields"><Field label="Reviewer" value={reviewer} onChange={setReviewer} /><label className="field"><span>Reviewer notes / rejection reason</span><textarea placeholder="Describe what you changed or why this PO should be rejected…" value={notes} onChange={(event) => setNotes(event.target.value)} /></label></div>
          {error && <p className="inline-error">{error}</p>}{message && <p className="inline-warning">{message}</p>}
          <button className="button primary wide" disabled={submitting} onClick={approve}><Check size={17} />{submitting ? 'Submitting…' : 'Approve with changes'}</button>
          <button className="button danger-button wide" disabled={submitting} onClick={reject}><X size={17} /> Reject purchase order</button>
          <p className="decision-help">Approval reruns RAG and all validation rules. An order is created only if every check passes.</p>
        </div>
      </aside>
    </div>
  </section>
}
