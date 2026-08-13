import { CheckCircle2, CircleAlert, XCircle } from 'lucide-react'

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const kind = normalized === 'approved' || normalized === 'draft'
    ? 'success'
    : normalized === 'rejected' ? 'danger' : 'warning'
  const Icon = kind === 'success' ? CheckCircle2 : kind === 'danger' ? XCircle : CircleAlert
  return <span className={`badge ${kind}`}><Icon size={13} />{status.replace('_', ' ')}</span>
}
