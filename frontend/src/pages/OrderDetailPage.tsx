import { ArrowLeft, CheckCircle2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/PageState'
import { StatusBadge } from '../components/StatusBadge'
import type { DraftOrder } from '../types'
import { money, shortDate } from '../utils'

export function OrderDetailPage() {
  const { orderId = '' } = useParams()
  const [order, setOrder] = useState<DraftOrder | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.getOrder(orderId).then(setOrder).catch((err: Error) => setError(err.message)) }, [orderId])
  if (error) return <section className="page"><ErrorState message={error} /></section>
  if (!order) return <section className="page"><LoadingState /></section>
  const po = order.order_data
  return <section className="page detail-page">
    <Link to="/orders" className="back-link"><ArrowLeft size={16} /> Processed orders</Link>
    <div className="detail-title"><div><p className="eyebrow">Validated purchase order</p><h1>{order.po_number}</h1><p>{order.customer_name} · received {shortDate(order.created_at)}</p></div><StatusBadge status={order.status} /></div>
    <div className="success-banner"><CheckCircle2 /><div><strong>All validation checks passed</strong><span>Customer, product, pricing, address, terms, and totals were verified.</span></div></div>
    <div className="detail-grid">
      <div className="panel span-two"><div className="panel-heading"><h2>Line items</h2><span>{po.line_items.length} items</span></div><div className="line-table"><div className="line-head"><span>Item</span><span>Qty</span><span>Unit price</span><span>Total</span></div>{po.line_items.map((line) => <div className="line-row" key={line.line_number}><span><strong>{line.resolved_sku ?? line.raw_sku}</strong><small>{line.raw_description}</small></span><span>{line.quantity}</span><span>{money(line.unit_price, order.currency)}</span><span>{money(line.line_total, order.currency)}</span></div>)}</div><div className="totals"><span>Subtotal <strong>{money(po.subtotal, order.currency)}</strong></span><span>Tax <strong>{money(po.tax, order.currency)}</strong></span><span className="grand-total">Total <strong>{money(po.total, order.currency)}</strong></span></div></div>
      <div className="panel"><h2>Order details</h2><dl><div><dt>Issue date</dt><dd>{shortDate(po.issue_date)}</dd></div><div><dt>Delivery date</dt><dd>{shortDate(po.requested_delivery_date)}</dd></div><div><dt>Payment terms</dt><dd>{po.payment_terms ?? '—'}</dd></div><div><dt>Currency</dt><dd>{po.currency}</dd></div></dl></div>
      <div className="panel"><h2>Ship to</h2><p className="address">{po.shipping_address ?? 'No shipping address provided'}</p><dl><div><dt>Customer ID</dt><dd className="mono">{po.resolved_customer_id?.slice(0, 12)}…</dd></div><div><dt>Run ID</dt><dd className="mono">{order.run_id.slice(0, 12)}…</dd></div></dl></div>
    </div>
  </section>
}
