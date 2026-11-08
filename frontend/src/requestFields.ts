import { type Field } from './lib/api'

export type Payload = Record<string, unknown>
export function defaultsFor(fields: Field[]): Payload {
  return Object.fromEntries(fields.filter((field) => (field.request_field || field.field_type === 'exclusive') && field.field_type !== 'unsupported' && (field.default !== undefined && field.default !== null || field.required && field.options.length === 1)).map((field) => {
    const value = field.default ?? (field.field_type === 'multiple' ? [field.options[0].value] : field.options[0].value)
    return [field.name, value]
  }))
}

export function activeFields(fields: Field[], payload: Payload): { field: Field; branch: boolean }[] {
  const byName = new Map(fields.map((field) => [field.name, field]))
  const children = new Set(fields.flatMap((field) => field.children || []))
  const result: { field: Field; branch: boolean }[] = []
  const visit = (field: Field, branch = false) => {
    result.push({ field, branch })
    if (field.field_type === 'exclusive') {
      const name = String(payload[field.name] ?? field.default ?? '')
      const child = byName.get(name)
      if (child && field.children?.includes(name)) visit(child, true)
    } else if (field.field_type === 'layout') for (const name of field.children || []) visit(byName.get(name)!, branch)
  }
  for (const field of fields) if (!children.has(field.name)) visit(field)
  return result
}

export function activeValues(fields: Field[], payload: Payload): Payload {
  return Object.fromEntries(activeFields(fields, payload).filter(({ field }) => (field.request_field || field.field_type === 'exclusive') && payload[field.name] !== undefined).map(({ field }) => [field.name, payload[field.name]]))
}

export function requestPayload(fields: Field[], payload: Payload): Payload {
  return Object.fromEntries(activeFields(fields, payload).filter(({ field }) => field.request_field && payload[field.name] !== undefined).map(({ field }) => {
    let value = payload[field.name]
    if (field.field_type === 'date_range' && Array.isArray(value)) value = [value.join('/')]
    else if (field.field_type === 'location' && Array.isArray(value)) value = { latitude: value[0], longitude: value[1] }
    else if (field.field_type === 'choice' && field.wire_type === 'array') value = [value]
    return [field.name, value]
  }))
}

export function fieldErrors(fields: Field[], payload: Payload, complete = true): string[] {
  const errors: string[] = []
  for (const { field, branch } of activeFields(fields, payload)) {
    const value = payload[field.name]
    if (field.field_type === 'exclusive') {
      if (complete && !field.children?.includes(String(value ?? field.default))) errors.push(`${field.label}：请选择一个分支。`)
      continue
    }
    if (!field.request_field) continue
    const empty = value === undefined || value === '' || (Array.isArray(value) && value.length === 0)
    if (empty) {
      if (complete && (field.required || branch)) errors.push(`${field.label}：请选择或填写必填参数。`)
      continue
    }
    const numeric = (item: unknown) => typeof item === 'number' && Number.isFinite(item)
    let valid = true
    if (field.field_type === 'multiple') {
      valid = Array.isArray(value) && value.every((item) => typeof item === 'string' || typeof item === 'boolean' || numeric(item))
      if (valid && field.integer) valid = (value as unknown[]).every((item) => Number.isInteger(item))
      if (valid && field.item_type === 'number') valid = (value as unknown[]).every(numeric)
      if (valid && field.item_type === 'boolean') valid = (value as unknown[]).every((item) => typeof item === 'boolean')
    } else if (['area', 'location'].includes(field.field_type)) {
      valid = Array.isArray(value) && value.length === (field.field_type === 'area' ? 4 : 2) && value.every(numeric)
      if (valid) {
        const [north, west, south, east] = field.field_type === 'area' ? value as number[] : [(value as number[])[0], (value as number[])[1], (value as number[])[0], (value as number[])[1]]
        const range = field.bounds?.range || { n: 90, w: -180, s: -90, e: 180 }
        valid = north <= range.n && south >= range.s && north >= south && west >= range.w && west <= range.e && east >= range.w && east <= range.e
        if (valid && field.field_type === 'area') {
          const spans: Record<string, number> = { lat: north - south, lon: east >= west ? east - west : east - west + 360 }
          valid = Object.entries(field.bounds?.minimum_extent || {}).every(([axis, min]) => spans[axis] + 1e-9 >= min) && Object.entries(field.bounds?.maximum_extent || {}).every(([axis, max]) => spans[axis] - 1e-9 <= max)
        }
      }
    } else if (field.field_type === 'date_range') {
      valid = Array.isArray(value) && value.length === 2 && value.every((item) => typeof item === 'string' && /^\d{4}-\d{2}(-\d{2})?$/.test(item))
      if (valid) { const [start, end] = value as string[]; valid = start <= end && start >= String(field.bounds?.minStart).slice(0, start.length) && end <= String(field.bounds?.maxEnd).slice(0, end.length) }
    } else if (field.field_type === 'object') {
      valid = typeof value === 'object' && value !== null && !Array.isArray(value)
      if (valid) valid = !fieldErrors(Object.values(field.properties || {}), value as Payload, complete).length
    } else if (field.field_type === 'number') valid = numeric(value) && (!field.integer || Number.isInteger(value)) && (field.minimum == null || (value as number) >= field.minimum) && (field.maximum == null || (value as number) <= field.maximum)
    else if (field.field_type === 'boolean') valid = typeof value === 'boolean'
    else if (field.field_type === 'text') valid = typeof value === 'string'
    else if (field.field_type === 'unsupported') valid = false
    if (field.options.length) {
      const selected = field.field_type === 'multiple' && Array.isArray(value) ? value : [value]
      valid = valid && selected.every((item) => field.options.some((option) => option.value === item))
    }
    if (!valid) errors.push(`${field.label}：参数类型、选项或范围不正确。`)
  }
  const names = new Set(fields.filter((field) => field.request_field || field.field_type === 'exclusive').map((field) => field.name))
  for (const name of Object.keys(payload)) if (!names.has(name)) errors.push(`${name}：当前数据集中没有此请求字段。`)
  return errors
}
