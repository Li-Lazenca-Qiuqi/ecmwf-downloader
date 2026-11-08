import { useId, useState } from 'react'
import { type Field } from '../../lib/api'

type Option = Field['options'][number]

export function resolveOptions(text: string, options: Option[], multiple: boolean, allowed?: unknown[]): unknown[] {
  const tokens = text.split(/[,，\n]/).map((token) => token.trim()).filter(Boolean)
  if (!tokens.length) throw new Error('请输入选项名称或 ID。')
  const values = tokens.map((token) => {
    const ids = options.filter((option) => String(option.value) === token)
    const matches = ids.length ? ids : options.filter((option) => option.label.toLocaleLowerCase() === token.toLocaleLowerCase())
    if (!matches.length) throw new Error(`未找到“${token}”，请使用完整名称或 ID。`)
    if (matches.length > 1) throw new Error(`“${token}”对应多个选项，请改用明确的 ID。`)
    const value = matches[0].value
    if (allowed !== undefined && !allowed.includes(value)) throw new Error(`“${token}”不适用于当前参数组合。`)
    return value
  })
  const unique = Array.from(new Set(values))
  if (!multiple && unique.length > 1) throw new Error('此字段为单选，请只输入一个选项。')
  return unique
}

export default function CommaOptionInput({ field, value, onChange, allowed, multiple = false, onSearch, compact = false }: {
  field: Pick<Field, 'name' | 'label' | 'options'>; value: unknown; onChange: (value: unknown) => void; allowed?: unknown[]; multiple?: boolean; onSearch?: (text: string) => void; compact?: boolean
}) {
  const id = useId()
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const apply = () => {
    try {
      const values = resolveOptions(text, field.options, multiple, allowed)
      onChange(multiple ? Array.from(new Set([...(Array.isArray(value) ? value : []), ...values])) : values[0])
      setText(''); setError(''); onSearch?.('')
    } catch (reason) { setError((reason as Error).message) }
  }
  const selectedText = (Array.isArray(value) ? value : value === undefined ? [] : [value]).map(String).join(', ')
  return <div className="comma-option-input" data-compact={compact}>
    <div className="comma-input-row"><input aria-label={`输入 ${field.name}`} aria-describedby={error ? id : undefined} aria-invalid={!!error} value={text} data-selected={compact && !!selectedText} placeholder={compact && selectedText ? selectedText : multiple ? '搜索或输入名称 / ID，多个用逗号分隔' : '搜索或输入选项名称 / ID'} onChange={(event) => { setText(event.target.value); setError(''); onSearch?.(event.target.value.split(/[,，\n]/).at(-1) || '') }} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); apply() } }} /><button type="button" className={compact ? "button comma-commit" : "button primary"} aria-label={(multiple ? "选入 " : "选择 ") + field.label} title="按 Enter 选择" disabled={!text.trim()} onClick={apply}>{compact ? "↵" : multiple ? '选入' : '选择'}</button></div>
    {error && <p id={id} className="inline-error" role="alert">{error}</p>}
  </div>
}
