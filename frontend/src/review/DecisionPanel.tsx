import { Check, CircleAlert, Database, X } from 'lucide-react'
import type { ReviewDetail, ValidationResult } from '../types'
import { reasonLabel } from '../utils'
import { Field } from './Field'

type Props = {
  review: ReviewDetail
  failures: ValidationResult[]
  reviewer: string
  notes: string
  error: string
  message: string
  submitting: boolean
  onReviewerChange: (value: string) => void
  onNotesChange: (value: string) => void
  onApprove: () => void
  onReject: () => void
}

export function DecisionPanel(props: Props) {
  const { review, failures } = props
  return (
    <aside className="decision-panel">
      <div className="panel sticky">
        <h2>Why it was flagged</h2>
        <div className="failure-list">
          {failures.length
            ? failures.map((failure) => (
                <div key={failure.code}>
                  <CircleAlert size={17} />
                  <span>
                    <strong>{reasonLabel(failure.code)}</strong>
                    <small>{failure.message}</small>
                  </span>
                </div>
              ))
            : review.reasons.map((reason) => (
                <div key={reason}>
                  <CircleAlert size={17} />
                  <strong>{reasonLabel(reason)}</strong>
                </div>
              ))}
        </div>

        {review.enrichment?.matches.length ? (
          <div className="rag-evidence">
            <p><Database size={15} /> RAG evidence</p>
            {review.enrichment.matches.slice(0, 4).map((match, index) => (
              <div key={`${match.source_title}-${index}`}>
                <strong>{match.entity_name ?? match.source_title}</strong>
                <span>{Math.round(match.similarity * 100)}% match · {match.source_title}</span>
              </div>
            ))}
          </div>
        ) : null}

        <div className="decision-fields">
          <Field label="Reviewer" value={props.reviewer} onChange={props.onReviewerChange} />
          <label className="field">
            <span>Reviewer notes / rejection reason</span>
            <textarea
              placeholder="Describe what you changed or why this PO should be rejected…"
              value={props.notes}
              onChange={(event) => props.onNotesChange(event.target.value)}
            />
          </label>
        </div>
        {props.error && <p className="inline-error">{props.error}</p>}
        {props.message && <p className="inline-warning">{props.message}</p>}
        <button className="button primary wide" disabled={props.submitting} onClick={props.onApprove}>
          <Check size={17} /> {props.submitting ? 'Submitting…' : 'Approve with changes'}
        </button>
        <button className="button danger-button wide" disabled={props.submitting} onClick={props.onReject}>
          <X size={17} /> Reject purchase order
        </button>
        <p className="decision-help">
          Approval reruns RAG and all validation rules. An order is created only if every check passes.
        </p>
      </div>
    </aside>
  )
}
