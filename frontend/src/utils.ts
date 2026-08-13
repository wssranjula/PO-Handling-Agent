export function money(value: number | string | null, currency = 'USD') {
  const number = Number(value ?? 0)
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(number)
  } catch {
    return `${currency} ${number.toFixed(2)}`
  }
}

export function shortDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    .format(new Date(value))
}

export function reasonLabel(code: string) {
  return code.replace(/^LINE_\d+_/, '').replaceAll('_', ' ').toLowerCase()
    .replace(/^\w/, (letter) => letter.toUpperCase())
}
