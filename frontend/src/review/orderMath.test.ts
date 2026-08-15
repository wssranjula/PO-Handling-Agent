import { describe, expect, it } from 'vitest'
import type { PurchaseOrder } from '../types'
import { updateLineItem, updateTax } from './orderMath'

const order: PurchaseOrder = {
  po_number: 'PO-1',
  issue_date: null,
  currency: 'USD',
  customer_name: 'Northstar',
  resolved_customer_id: 'CUST-NORTHSTAR',
  shipping_address: null,
  requested_delivery_date: null,
  payment_terms: null,
  subtotal: '90.00',
  tax: '5.00',
  total: '95.00',
  line_items: [{
    line_number: 1,
    raw_description: 'Mug',
    raw_sku: 'MUG-WHT',
    resolved_sku: 'MUG-WHITE-STD',
    quantity: 10,
    unit_price: 9,
    line_total: 90,
  }],
}

describe('review order calculations', () => {
  it('recalculates the line, subtotal, and total after a price correction', () => {
    const updated = updateLineItem(order, 0, 'unit_price', '7.50')

    expect(updated.line_items[0].line_total).toBe('75.00')
    expect(updated.subtotal).toBe('75.00')
    expect(updated.total).toBe('80.00')
  })

  it('recalculates the total after a tax correction', () => {
    const updated = updateTax(order, '10.00')

    expect(updated.subtotal).toBe('90.00')
    expect(updated.total).toBe('100.00')
  })
})
