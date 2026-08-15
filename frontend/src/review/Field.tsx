type FieldProps = {
  label: string
  value: string | number | null
  type?: string
  readOnly?: boolean
  onChange: (value: string) => void
}

export function Field({
  label,
  value,
  type = 'text',
  readOnly = false,
  onChange,
}: FieldProps) {
  return (
    <label className={`field ${readOnly ? 'derived-field' : ''}`}>
      <span>{label}</span>
      <input
        type={type}
        readOnly={readOnly}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}
