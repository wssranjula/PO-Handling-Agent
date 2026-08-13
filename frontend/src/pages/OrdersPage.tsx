import { ArrowUpRight, CheckCircle2, PackageCheck, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { EmptyState, ErrorState, LoadingState } from '../components/PageState'
import { StatusBadge } from '../components/StatusBadge'
import type { DraftOrder } from '../types'
import { money, shortDate } from '../utils'

export function OrdersPage() {
  const [orders, setOrders] = useState<DraftOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    api.listOrders().then(setOrders).catch((err: Error) => setError(err.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  return (
    <section className="page">
      <div className="page-heading">
        <div><p className="eyebrow">Clean queue</p><h1>Processed purchase orders</h1><p>Orders that passed extraction, RAG enrichment, and every business rule.</p></div>
        <button className="button secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </div>
      {!loading && !error && orders.length > 0 && (
        <div className="metric-strip">
          <div className="metric-icon green"><PackageCheck /></div>
          <div><strong>{orders.length}</strong><span>validated orders</span></div>
          <div className="metric-rule" />
          <div><strong>{money(orders.reduce((sum, order) => sum + Number(order.total), 0), orders[0]?.currency)}</strong><span>total order value</span></div>
          <div className="metric-note"><CheckCircle2 size={16} /> Ready for downstream processing</div>
        </div>
      )}
      {loading ? <LoadingState /> : error ? <ErrorState message={error} /> : orders.length === 0 ? (
        <EmptyState title="No processed orders yet" detail="Clean purchase orders will appear here after the agent validates them." />
      ) : (
        <div className="table-card">
          <table>
            <thead><tr><th>PO number</th><th>Customer</th><th>Received</th><th>Lines</th><th>Total</th><th>Status</th><th /></tr></thead>
            <tbody>{orders.map((order) => (
              <tr key={order.id}>
                <td><Link className="po-link" to={`/orders/${order.id}`}>{order.po_number}</Link></td>
                <td><strong>{order.customer_name}</strong><small>{order.order_data.shipping_address ?? 'No ship-to address'}</small></td>
                <td>{shortDate(order.created_at)}</td>
                <td>{order.order_data.line_items.length}</td>
                <td className="money-cell">{money(order.total, order.currency)}</td>
                <td><StatusBadge status={order.status} /></td>
                <td><Link className="icon-link" to={`/orders/${order.id}`} aria-label={`Open ${order.po_number}`}><ArrowUpRight size={17} /></Link></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
