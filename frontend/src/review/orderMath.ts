import type { LineItem, PurchaseOrder } from '../types'

function amount(value: number | string | null): number {
  const parsed = Number(value ?? 0)
  return Number.isFinite(parsed) ? parsed : 0
}

function moneyValue(value: number): string {
  return value.toFixed(2)
}

export function recalculateOrder(order: PurchaseOrder): PurchaseOrder {
  const lineItems = order.line_items.map((line) => {
    const hasInputs = line.quantity !== null && line.unit_price !== null
    return {
      ...line,
      line_total: hasInputs
        ? moneyValue(amount(line.quantity) * amount(line.unit_price))
        : null,
    }
  })
  const subtotal = lineItems.reduce(
    (sum, line) => sum + amount(line.line_total),
    0,
  )

  return {
    ...order,
    line_items: lineItems,
    subtotal: moneyValue(subtotal),
    total: moneyValue(subtotal + amount(order.tax)),
  }
}

export function updateLineItem(
  order: PurchaseOrder,
  index: number,
  key: keyof LineItem,
  value: string,
): PurchaseOrder {
  const lineItems = order.line_items.map((line, position) => {
    if (position !== index) return line
    const updated = { ...line, [key]: value || null }
    if (key === 'raw_sku') updated.resolved_sku = null
    return updated
  })
  return recalculateOrder({ ...order, line_items: lineItems })
}

export function updateTax(order: PurchaseOrder, tax: string): PurchaseOrder {
  return recalculateOrder({ ...order, tax: tax || null })
}
