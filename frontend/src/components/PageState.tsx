import { AlertTriangle, Inbox } from 'lucide-react'

export function LoadingState() {
  return <div className="page-state"><span className="spinner" /><p>Loading purchase orders…</p></div>
}

export function ErrorState({ message }: { message: string }) {
  return <div className="page-state error-state"><AlertTriangle /><h3>Couldn’t load this view</h3><p>{message}</p></div>
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="page-state empty-state"><Inbox /><h3>{title}</h3><p>{detail}</p></div>
}
