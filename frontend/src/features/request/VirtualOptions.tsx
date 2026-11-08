import { useEffect, useRef, useState } from 'react'
import { type Field } from '../../lib/api'

type Option = Field['options'][number]
export default function VirtualOptions({ options, selected, available, toggle }: { options: Option[]; selected: unknown[]; available: (value: unknown) => boolean; toggle: (option: Option, checked: boolean) => void }) {
  const viewport = useRef<HTMLDivElement>(null)
  const [top, setTop] = useState(0)
  const contentKey = JSON.stringify(options.map((option) => option.value))
  useEffect(() => { setTop(0); if (viewport.current) viewport.current.scrollTop = 0 }, [contentKey])
  const rowHeight = 52
  const start = Math.max(0, Math.floor(top / rowHeight) - 2)
  return <div ref={viewport} className="virtual-options" role="group" aria-label="可选项，方向键浏览" onScroll={(event) => setTop(event.currentTarget.scrollTop)} onKeyDown={(event) => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
    const current = Number((event.target as HTMLInputElement).dataset.optionIndex)
    if (!Number.isInteger(current)) return
    event.preventDefault()
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : Math.max(0, Math.min(options.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1)))
    viewport.current!.scrollTop = next * rowHeight
    setTop(next * rowHeight)
    requestAnimationFrame(() => requestAnimationFrame(() => viewport.current?.querySelector<HTMLInputElement>(`[data-option-index="${next}"]`)?.focus()))
  }}><div style={{ height: options.length * rowHeight, position: 'relative' }}>{options.slice(start, start + 10).map((option, index) => <label className="option virtual-option" key={JSON.stringify(option.value)} style={{ top: (start + index) * rowHeight, height: rowHeight }}><input type="checkbox" data-option-index={start + index} aria-label={`${option.label} (${String(option.value)})`} checked={selected.includes(option.value)} disabled={!available(option.value) && !selected.includes(option.value)} onChange={(event) => toggle(option, event.target.checked)} /><span title={option.label}>{option.label}{option.label !== String(option.value) && <small>{String(option.value)}</small>}</span></label>)}</div></div>
}
