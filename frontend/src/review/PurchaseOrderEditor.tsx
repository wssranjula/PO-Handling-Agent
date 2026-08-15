import { Save } from 'lucide-react'
import type { LineItem, PurchaseOrder } from '../types'
import { Field } from './Field'
import { updateLineItem, updateTax } from './orderMath'

type Props = {
  order: PurchaseOrder
  onChange: (order: PurchaseOrder) => void
}

export function PurchaseOrderEditor({ order, onChange }: Props) {
  const update = <K extends keyof PurchaseOrder>(
    key: K,
    value: PurchaseOrder[K],
  ) => onChange({ ...order, [key]: value })

  const updateLine = (index: number, key: keyof LineItem, value: string) => {
    onChange(updateLineItem(order, index, key, value))
  }

  return (
    <div className="review-form">
      <div className="panel">
        <div className="panel-heading">
          <h2>Purchase order</h2>
          <span className="edited-hint">
            <Save size={14} /> Changes are submitted on approval
          </span>
        </div>
        <div className="form-grid">
          <Field label="PO number" value={order.po_number} onChange={(value) => update('po_number', value)} />
          <Field label="Issue date" type="date" value={order.issue_date} onChange={(value) => update('issue_date', value || null)} />
          <Field label="Customer" value={order.customer_name} onChange={(value) => update('customer_name', value)} />
          <Field label="Currency" value={order.currency} onChange={(value) => update('currency', value.toUpperCase())} />
          <label className="field full">
            <span>Shipping address</span>
            <textarea value={order.shipping_address ?? ''} onChange={(event) => update('shipping_address', event.target.value)} />
          </label>
          <Field label="Requested delivery" type="date" value={order.requested_delivery_date} onChange={(value) => update('requested_delivery_date', value || null)} />
          <Field label="Payment terms" value={order.payment_terms} onChange={(value) => update('payment_terms', value)} />
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <h2>Line items</h2>
          <span>{order.line_items.length} lines</span>
        </div>
        <div className="editable-lines">
          {order.line_items.map((line, index) => (
            <div className="editable-line" key={line.line_number}>
              <span className="line-number">{line.line_number}</span>
              <Field label="SKU" value={line.resolved_sku ?? line.raw_sku} onChange={(value) => updateLine(index, 'raw_sku', value)} />
              <Field label="Description" value={line.raw_description} onChange={(value) => updateLine(index, 'raw_description', value)} />
              <Field label="Quantity" type="number" value={line.quantity} onChange={(value) => updateLine(index, 'quantity', value)} />
              <Field label="Unit price" type="number" value={line.unit_price} onChange={(value) => updateLine(index, 'unit_price', value)} />
              <Field label="Line total" type="number" readOnly value={line.line_total} onChange={() => undefined} />
            </div>
          ))}
        </div>
        <div className="form-grid totals-form">
          <Field label="Subtotal" type="number" readOnly value={order.subtotal} onChange={() => undefined} />
          <Field label="Tax" type="number" value={order.tax} onChange={(value) => onChange(updateTax(order, value))} />
          <Field label="Total" type="number" readOnly value={order.total} onChange={() => undefined} />
        </div>
      </div>
    </div>
  )
}
