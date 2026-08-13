export type LineItem = {
  line_number: number
  raw_description: string | null
  raw_sku: string | null
  resolved_sku: string | null
  quantity: number | string | null
  unit_price: number | string | null
  line_total: number | string | null
}

export type PurchaseOrder = {
  po_number: string | null
  issue_date: string | null
  currency: string | null
  customer_name: string | null
  resolved_customer_id: string | null
  shipping_address: string | null
  requested_delivery_date: string | null
  payment_terms: string | null
  subtotal: number | string | null
  tax: number | string | null
  total: number | string | null
  line_items: LineItem[]
}

export type DraftOrder = {
  id: string
  run_id: string
  customer_id: string
  customer_name: string
  po_number: string
  currency: string
  total: number | string
  status: string
  order_data: PurchaseOrder
  created_at: string
}

export type ValidationResult = {
  code: string
  passed: boolean
  message: string
  severity: string
}

export type ReviewSummary = {
  id: string
  run_id: string
  status: string
  reasons: string[]
  resolution: Record<string, unknown> | null
  created_at: string
}

export type ReviewDetail = ReviewSummary & {
  extracted_data: { order?: PurchaseOrder; overall_confidence?: number } | null
  validation_results: ValidationResult[] | null
  enrichment: {
    resolved_order: PurchaseOrder
    matches: Array<{ source_title: string; entity_name: string | null; similarity: number }>
  } | null
  error: Record<string, unknown> | null
}
