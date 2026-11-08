import { useId, useState } from 'react'
import { type Field } from '../../lib/api'
import CardSelect from '../../CardSelect'
import CommaOptionInput from './CommaOptionInput'
import OptionCombobox from './OptionCombobox'

export default function ChoicePicker({ field, value, onChange, allowed, compact = false }: { field: Field; value: unknown; onChange: (value: unknown) => void; allowed?: unknown[]; compact?: boolean }) {
  const id = useId()
  const [search, setSearch] = useState('')
  const available = (item: unknown) => allowed === undefined || allowed.includes(item)
  const variable = ['variable', 'variables'].includes(field.name.toLowerCase())
  const options = field.options.filter((option) => `${option.label} ${option.value}`.toLowerCase().includes(search.trim().toLowerCase()) || option.value === value)
  if (compact) return <OptionCombobox field={field} value={value} onChange={onChange} allowed={allowed} multiple={false} />
  return <div className="choice-picker">
    {variable ? <input type="search" aria-label={"搜索 " + field.name} placeholder="搜索变量名称或 ID" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') event.preventDefault() }} /> : field.options.length > 4 ? <CommaOptionInput compact={compact} field={field} value={value} onChange={onChange} allowed={allowed} onSearch={setSearch} /> : <details className="choice-entry"><summary aria-label={field.label + " 直接输入"}>输入</summary><CommaOptionInput field={field} value={value} onChange={onChange} allowed={allowed} onSearch={setSearch} /></details>}
    {field.required && field.options.length === 1 && value === field.options[0].value ? <p className="fixed-value">{field.options[0].label}<small>固定选项</small></p> : field.options.length <= 4 ? <div className="choice-options" role="radiogroup" aria-label={field.label}>
      {!field.required && <label className="choice-card"><input type="radio" name={id} checked={value === undefined} onChange={() => onChange(undefined)} />不设置</label>}
      {(variable ? options : field.options).map((option) => <label className={`choice-card ${value === option.value ? 'selected' : ''}`} key={JSON.stringify(option.value)}><input type="radio" name={id} checked={value === option.value} disabled={!available(option.value)} onChange={() => onChange(option.value)} />{option.label}</label>)}
    </div> : <CardSelect label={`${field.label} (${field.name})`} value={value === undefined ? '' : JSON.stringify(value)}
      onChange={key => onChange(field.options.find(option => JSON.stringify(option.value) === key)?.value)}
      options={[
        { value: '', label: field.required ? '请选择' : '不设置' },
        ...options.map(option => ({ value: JSON.stringify(option.value), label: option.label, disabled: !available(option.value) })),
      ]} />}
  </div>
}
