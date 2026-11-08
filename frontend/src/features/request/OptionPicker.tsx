import { useId, useMemo, useState } from 'react'
import VirtualOptions from './VirtualOptions'
import CommaOptionInput from './CommaOptionInput'
import OptionCombobox from './OptionCombobox'
import { ChevronDown } from 'lucide-react'
import { type Field } from '../../lib/api'

type Option = Field['options'][number]

export default function OptionPicker({ field, value, onChange, allowed, compact = false }: {
  field: Field; value: unknown; onChange: (value: unknown) => void; allowed?: unknown[]; compact?: boolean
}) {
  const id = useId()
  const variable = ['variable', 'variables'].includes(field.name.toLowerCase())
  const [search, setSearch] = useState('')
  const [allSelected, setAllSelected] = useState(false)
  const labels = useMemo(() => new Map(field.options.map((option) => [option.value, option.label])), [field.options])
  const groups = useMemo(() => {
    const result = new Map<string, Option[]>()
    for (const option of field.options) {
      const names = option.groups?.length ? option.groups : option.group ? [option.group] : ['未分类']
      for (const name of new Set(names)) result.set(name, [...(result.get(name) || []), option])
    }
    return Array.from(result, ([name, options]) => ({ name, options }))
  }, [field.options])
  const [expanded, setExpanded] = useState(() => new Set(field.open_groups?.length ? field.open_groups : groups.slice(0, 1).map((group) => group.name)))
  const grouped = field.options.some((option) => option.group || option.groups?.length)
  const selected = Array.isArray(value) ? value : []
  const query = search.trim().toLowerCase()
  const matches = (option: Option, group = '') => `${option.label} ${option.value} ${group}`.toLowerCase().includes(query)
  const filtered = field.options.filter((option) => matches(option, (option.groups || [option.group || '']).join(' ')))
  const available = (item: unknown) => allowed === undefined || allowed.some((candidate) => candidate === item)
  const select = (options: Option[]) => onChange(Array.from(new Set([...selected, ...options.filter((option) => available(option.value)).map((option) => option.value)])))
  const clear = (options: Option[]) => {
    const remove = new Set(options.map((option) => option.value))
    const next = selected.filter((item) => !remove.has(item))
    onChange(next.length ? next : undefined)
  }
  const renderOptions = (options: Option[]) => options.length > 100 ? <VirtualOptions options={options} selected={selected} available={available} toggle={(option, checked) => checked ? select([option]) : clear([option])} /> : <div className="option-list">{options.map((option) => <label className="option" key={JSON.stringify(option.value)}>
    <input type="checkbox" aria-label={`${option.label} (${String(option.value)})`} checked={selected.includes(option.value)} disabled={!available(option.value) && !selected.includes(option.value)} onChange={(event) => event.target.checked ? select([option]) : clear([option])} />
    <span>{option.label}{option.label !== String(option.value) && <small>{String(option.value)}</small>}</span>
  </label>)}</div>
  const selectedValues = () => <div className={variable ? "selected-values variable-selected-values" : "selected-values"} aria-label={`${field.name} 已选项`}>{(variable || allSelected ? selected : selected.slice(0, 8)).map((item) => <button type="button" key={JSON.stringify(item)} className="selected-value" onClick={() => clear([{ value: item, label: String(item) } as Option])} title="取消此项">{labels.get(item) || String(item)} ×</button>)}{!variable && selected.length > 8 && <button type="button" className="text-button" onClick={() => setAllSelected(!allSelected)}>{allSelected ? '收起已选' : `查看全部已选（${selected.length}）`}</button>}{!selected.length && <span className="selected-placeholder">{variable ? "尚未选择变量" : "尚未选择选项"}</span>}</div>
  if (field.options.length < 5) return <div className="short-option-picker">
    {variable && selectedValues()}
    <div className="choice-options" role="group" aria-label={field.label}>{field.options.map((option) => <label className={['choice-card', selected.includes(option.value) ? 'selected' : ''].join(' ')} key={JSON.stringify(option.value)}><input type="checkbox" aria-label={option.label + " (" + option.value + ")"} checked={selected.includes(option.value)} disabled={!available(option.value) && !selected.includes(option.value)} onChange={(event) => event.target.checked ? select([option]) : clear([option])} />{option.label}</label>)}</div>
  </div>
  if (compact) return <OptionCombobox field={field} value={value} onChange={onChange} allowed={allowed} multiple />
  return <div className={variable ? "option-picker variable-option-picker" : "option-picker"}>
    {selectedValues()}
    {variable ? <input type="search" aria-label={"搜索 " + field.name} placeholder="搜索变量名称、ID 或分类" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') event.preventDefault() }} /> : <CommaOptionInput field={field} value={value} onChange={onChange} allowed={allowed} multiple onSearch={setSearch} />}
    <div className="option-tools"><span>已选 {new Set(selected).size} / {field.options.length}</span>
      <button type="button" className="text-button" onClick={() => select(filtered)}>全选当前结果</button>
      <button type="button" className="text-button" onClick={() => onChange(undefined)}>清空</button>
      {grouped && !query && <><button type="button" className="text-button" onClick={() => setExpanded(new Set(groups.map((group) => group.name)))}>展开全部</button><button type="button" className="text-button" onClick={() => setExpanded(new Set())}>收起全部</button></>}
    </div>

    {grouped ? <div className="option-groups">{variable && !filtered.length && <p className="empty-option-results">没有匹配的变量。</p>}{groups.map((group, index) => {
      const options = group.options.filter((option) => matches(option, group.name))
      if (!options.length) return null
      const open = !!query || expanded.has(group.name)
      const panelId = `${id}-${index}`
      return <section className="option-group" key={group.name}>
        <button type="button" className="option-group-heading" aria-expanded={open} aria-controls={panelId} onClick={() => setExpanded((current) => {
          const next = new Set(current)
          if (next.has(group.name)) next.delete(group.name); else next.add(group.name)
          return next
        })}><ChevronDown size={15} className={open ? 'expanded' : ''} /><span>{group.name}</span><small>已选 {group.options.filter((option) => selected.includes(option.value)).length} / {group.options.length}{query ? ` · 匹配 ${options.length}` : ''}</small></button>
        {open && <div id={panelId} className="option-group-content" role="group" aria-label={`${group.name} 选项`}>
          <div className="option-tools"><button type="button" className="text-button" onClick={() => select(options)}>全选本组{query ? '匹配项' : ''}</button><button type="button" className="text-button" onClick={() => clear(options)}>清空本组{query ? '匹配项' : ''}</button></div>
          {renderOptions(options)}
        </div>}
      </section>
    })}</div> : variable ? <div className="variable-candidates">{filtered.length ? renderOptions(filtered) : <p className="empty-option-results">没有匹配的变量。</p>}</div> : <details className="option-candidates" open={!!query}><summary>浏览选项<span>{filtered.length} 项</span></summary>{renderOptions(filtered)}</details>}
    {!variable && !filtered.length && <p className="helper">没有匹配的选项。</p>}
  </div>
}
