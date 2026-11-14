import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react'
import { Check, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'

type SelectOption<T extends string> = {
  value: T
  label: string
  disabled?: boolean
  renderPanel?: (confirm: () => void) => ReactNode
}

function menuPosition(trigger: HTMLButtonElement, optionCount: number): CSSProperties | null {
  const rect = trigger.getBoundingClientRect()
  const viewportWidth = document.documentElement.clientWidth
  const viewportHeight = window.innerHeight
  if (rect.bottom <= 0 || rect.top >= viewportHeight) return null

  const width = Math.min(Math.max(rect.width, 168), viewportWidth - 16)
  const below = viewportHeight - rect.bottom - 16
  const above = rect.top - 16
  const openAbove = below < Math.min(240, optionCount * 36 + 12) && above > below
  return {
    left: Math.min(Math.max(8, rect.left), viewportWidth - width - 8),
    width,
    maxHeight: Math.min(320, openAbove ? above : below),
    ...(openAbove ? { bottom: viewportHeight - rect.top + 8 } : { top: rect.bottom + 8 }),
  }
}

export default function CardSelect<T extends string>({ label, value, options, onChange, selectedLabel, showLabel = false, className = '' }: {
  label: string
  value: T
  options: readonly SelectOption<T>[]
  onChange: (value: T) => void
  selectedLabel?: string
  showLabel?: boolean
  className?: string
}) {
  const id = useId()
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<CSSProperties | null>(null)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [panelIndex, setPanelIndex] = useState<number | null>(null)
  const panel = panelIndex === null ? undefined : options[panelIndex]
  const open = position !== null
  const selectedIndex = options.findIndex(option => option.value === value)
  const enabled = options.flatMap((option, index) => option.disabled ? [] : [index])
  const close = () => { setPanelIndex(null); setPosition(null) }

  function show(button: HTMLButtonElement, fallback = enabled[0]) {
    setActiveIndex(enabled.includes(selectedIndex) ? selectedIndex : (fallback ?? -1))
    setPosition(menuPosition(button, options.length))
  }

  function back() {
    trigger.current?.focus()
    setActiveIndex(panelIndex ?? -1)
    setPanelIndex(null)
    if (trigger.current) setPosition(menuPosition(trigger.current, options.length))
  }

  function choose(index: number) {
    const option = options[index]
    if (!option || option.disabled) return
    if (option.renderPanel) {
      setPanelIndex(index)
      if (trigger.current) setPosition(menuPosition(trigger.current, 4))
    } else {
      onChange(option.value)
      close()
    }
  }

  function handleKey(event: KeyboardEvent<HTMLButtonElement>) {
    const { key } = event
    if (open && key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      if (panel) back()
      else close()
    } else if (key === 'ArrowDown' || key === 'ArrowUp') {
      event.preventDefault()
      const step = key === 'ArrowDown' ? 1 : -1
      if (!open) {
        show(event.currentTarget, step === 1 ? enabled[0] : enabled.at(-1))
      } else {
        const next = Math.max(0, Math.min(enabled.length - 1, enabled.indexOf(activeIndex) + step))
        setActiveIndex(enabled[next] ?? -1)
      }
    } else if (open && (key === 'Home' || key === 'End')) {
      event.preventDefault()
      setActiveIndex((key === 'Home' ? enabled[0] : enabled.at(-1)) ?? -1)
    } else if (open && (key === 'Enter' || key === ' ' || (key === 'ArrowRight' && !panel && options[activeIndex]?.renderPanel))) {
      event.preventDefault()
      choose(activeIndex)
    }
  }

  useEffect(() => {
    if (!open) return
    function reposition(event: Event) {
      if (event.target !== menu.current && trigger.current) setPosition(menuPosition(trigger.current, panel ? 4 : options.length))
    }
    function dismissOutside(event: PointerEvent) {
      const target = event.target as Node
      if (!trigger.current?.contains(target) && !menu.current?.contains(target)) {
        setPanelIndex(null)
        setPosition(null)
      }
    }
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    document.addEventListener('pointerdown', dismissOutside)
    return () => {
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
      document.removeEventListener('pointerdown', dismissOutside)
    }
  }, [open, options.length, panel])

  useEffect(() => {
    if (open && !panel) menu.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [open, activeIndex, panel])

  return <div className={`card-select ${className}`} onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget)) close()
  }}>
    {showLabel && <span className="card-select-label">{label}</span>}
    <button type="button" ref={trigger} className="card-select-trigger" role="combobox"
      aria-label={label} aria-haspopup={panel ? 'dialog' : 'listbox'} aria-expanded={open} aria-controls={open ? id : undefined}
      aria-activedescendant={open && !panel && activeIndex >= 0 ? `${id}-${activeIndex}` : undefined}
      disabled={!enabled.length} onKeyDown={handleKey}
      onClick={event => open ? close() : show(event.currentTarget)}>
      <span>{selectedLabel ?? options[selectedIndex]?.label ?? '请选择'}</span>
      <ChevronDown size={15} aria-hidden="true" />
    </button>
    {position && (panel ? <div className="card-select-menu card-select-panel" id={id} ref={menu} style={position}
      role="dialog" aria-label={panel.label} onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); back() }
      }}>
      <button type="button" className="text-button card-select-back" onClick={back}>
        <ChevronLeft size={14} aria-hidden="true" />返回上一级
      </button>
      {panel.renderPanel?.(() => { trigger.current?.focus(); close() })}
    </div> : <div className="card-select-menu" id={id} ref={menu} style={position}
      role="listbox" aria-label={label} onMouseDown={event => event.preventDefault()}>
      {options.map((option, index) => <div key={option.value} id={`${id}-${index}`} role="option"
        className={index === activeIndex ? 'card-select-option is-active' : 'card-select-option'}
        aria-selected={option.value === value} aria-disabled={option.disabled || undefined} onClick={() => choose(index)}>
        <span>{option.label}</span>
        {option.renderPanel ? <ChevronRight size={15} aria-hidden="true" />
          : option.value === value && <Check size={15} aria-hidden="true" />}
      </div>)}
    </div>)}
  </div>
}
