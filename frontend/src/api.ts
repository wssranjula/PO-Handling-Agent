import type { DraftOrder, PurchaseOrder, ReviewDetail, ReviewSummary } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listOrders: () => request<DraftOrder[]>('/orders'),
  getOrder: (id: string) => request<DraftOrder>(`/orders/${id}`),
  listReviews: (status = 'open') => request<ReviewSummary[]>(`/reviews?status=${status}`),
  getReview: (id: string) => request<ReviewDetail>(`/reviews/${id}`),
  approveReview: (id: string, correctedOrder: PurchaseOrder, reviewer: string, notes: string) =>
    request<{ status: string; review_reasons: string[]; draft_order_id: string | null }>(
      `/reviews/${id}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({ corrected_order: correctedOrder, reviewer, notes: notes || null }),
      },
    ),
  rejectReview: (id: string, reviewer: string, reason: string) =>
    request<{ status: string }>(`/reviews/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reviewer, reason }),
    }),
}
