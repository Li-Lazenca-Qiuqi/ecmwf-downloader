import { useEffect, useId, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { type Field } from '../../lib/api'
import { resolveOptions } from './CommaOptionInput'
import VirtualOptions from './VirtualOptions'

export default function OptionCombobox({ field, value, onChange, allowed, multiple }: {
  field: Field; value: unknown; onChange: (value: unknown) => void; allowed?: unknown[]; multiple: boolean
}) {
  const id = useId()
  const root = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const skipFocus = useRef(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState('')
  const [placement, setPlacement] = useState({ above: false, height: 320 })
  const selected = multiple ? Array.isArray(value) ? value : [] : value === undefined ? [] : [value]
  const committed = selected.map(String).join(', ')
  const query = dirty ? draft.split(/[,，\n]/).at(-1)!.trim().toLowerCase() : ''
  const options = field.options.filter((option) => (option.label + ' ' + option.value).toLowerCase().includes(query))
  const available = (item: unknown) => allowed === undefined || allowed.includes(item)
  const dismiss = () => { setOpen(false); setEditing(false); setDirty(false); setError('') }
  const show = () => {
    const rect = root.current!.getBoundingClientRect()
    const below = window.innerHeight - rect.bottom
    const above = below < 240 && rect.top > below
    setPlacement({ above, height: Math.max(120, Math.min(320, (above ? rect.top : below) - 16)) })
    setOpen(true)
  }
  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => { if (!root.current!.contains(event.target as Node)) dismiss() }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  const change = (next: unknown[]) => {
    onChange(multiple ? next.length ? next : undefined : next[0])
    setEditing(false); setDirty(false); setError('')
  }
  const toggle = (option: Field['options'][number], checked: boolean) => {
    const next = multiple ? checked ? Array.from(new Set([...selected, option.value])) : selected.filter((item) => item !== option.value) : [option.value]
    change(next)
    if (!multiple) dismiss()
  }
  const apply = () => {
    if (!dirty) { dismiss(); return }
    try {
      change(draft.trim() ? resolveOptions(draft, field.options, multiple, allowed) : [])
      setOpen(false)
    } catch (reason) { setError((reason as Error).message) }
  }
  const escape = () => {
    dismiss()
    if (document.activeElement !== input.current) { skipFocus.current = true; input.current!.focus() }
  }
  return <div className="option-combobox" ref={root} onBlur={(event) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) dismiss()
  }} onKeyDown={(event) => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); escape() }
  }}>
    <div className="option-combobox-control">
      <input ref={input} role="combobox" aria-haspopup="dialog" aria-expanded={open} aria-controls={id} aria-label={'输入 ' + field.name}
        aria-invalid={!!error} aria-describedby={error ? id + '-error' : undefined} autoComplete="off" value={editing ? draft : committed}
        placeholder={multiple ? '输入值，逗号分隔' : '输入选项'} title="输入名称或 ID，按 Enter 应用；Esc 取消编辑"
        onFocus={(event) => {
          if (skipFocus.current) { skipFocus.current = false; return }
          setEditing(true); setDraft(committed); setDirty(false); show(); event.currentTarget.select()
        }}
        onClick={() => { if (!open) show() }}
        onChange={(event) => { setEditing(true); setDraft(event.target.value); setDirty(true); setError(''); show() }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') { event.preventDefault(); apply() }
          if (event.key === 'ArrowDown') {
            event.preventDefault(); show()
            requestAnimationFrame(() => root.current?.querySelector<HTMLInputElement>('.option-combobox-menu input:not(:disabled)')?.focus())
          }
        }} />
      <button type="button" className="option-combobox-toggle" aria-label={(open ? '收起 ' : '展开 ') + field.label} aria-expanded={open} aria-controls={id}
        onPointerDown={(event) => event.preventDefault()} onClick={() => open ? dismiss() : show()}><ChevronDown size={15} className={open ? 'expanded' : ''} /></button>
    </div>
    {error && <p id={id + '-error'} className="inline-error" role="alert">{error}</p>}
    {open && <div id={id} role="dialog" aria-label={field.label + ' 候选'} className={'option-combobox-menu' + (placement.above ? ' opens-above' : '')} style={{ maxHeight: placement.height }}>
      <div className="option-tools"><span>已选 {selected.length} / {field.options.length}</span>
        {multiple && <button type="button" className="text-button" onClick={() => change(Array.from(new Set([...selected, ...options.filter((option) => available(option.value)).map((option) => option.value)])))}>全选当前结果</button>}
        <button type="button" className="text-button" onClick={() => change([])}>清空</button>
      </div>
      {multiple && options.length > 100 ? <VirtualOptions options={options} selected={selected} available={available} toggle={toggle} /> : <div className="option-list">{options.map((option) => <label className="option" key={JSON.stringify(option.value)}>
        <input type={multiple ? 'checkbox' : 'radio'} name={id} aria-label={option.label + ' (' + option.value + ')'} checked={selected.includes(option.value)}
          disabled={!available(option.value) && !selected.includes(option.value)} onChange={(event) => toggle(option, event.target.checked)} /><span>{option.label}</span>
      </label>)}</div>}
      {!options.length && <p className="helper">没有匹配的选项。</p>}
    </div>}
  </div>
}
