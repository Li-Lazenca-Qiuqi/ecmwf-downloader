import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import { Check, ChevronDown } from 'lucide-react'

type SelectOption<T extends string> = { value: T; label: string; disabled?: boolean }

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

export default function CardSelect<T extends string>({ label, value, options, onChange, showLabel = false, className = '' }: {
  label: string
  value: T
  options: readonly SelectOption<T>[]
  onChange: (value: T) => void
  showLabel?: boolean
  className?: string
}) {
  const id = useId()
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<CSSProperties | null>(null)
  const [activeIndex, setActiveIndex] = useState(-1)
  const open = position !== null
  const selectedIndex = options.findIndex(option => option.value === value)
  const enabled = options.flatMap((option, index) => option.disabled ? [] : [index])
  const close = () => setPosition(null)

  function show(button: HTMLButtonElement, fallback = enabled[0]) {
    setActiveIndex(enabled.includes(selectedIndex) ? selectedIndex : (fallback ?? -1))
    setPosition(menuPosition(button, options.length))
  }

  function choose(option: SelectOption<T>) {
    if (option.disabled) return
    onChange(option.value)
    close()
  }

  function handleKey(event: KeyboardEvent<HTMLButtonElement>) {
    const { key } = event
    if (open && key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close()
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
    } else if (open && (key === 'Enter' || key === ' ')) {
      event.preventDefault()
      const option = options[activeIndex]
      if (option) choose(option)
    }
  }

  useEffect(() => {
    if (!open) return
    function reposition(event: Event) {
      if (event.target !== menu.current && trigger.current) setPosition(menuPosition(trigger.current, options.length))
    }
    function dismissOutside(event: PointerEvent) {
      const target = event.target as Node
      if (!trigger.current?.contains(target) && !menu.current?.contains(target)) setPosition(null)
    }
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    document.addEventListener('pointerdown', dismissOutside)
    return () => {
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
      document.removeEventListener('pointerdown', dismissOutside)
    }
  }, [open, options.length])

  useEffect(() => {
    if (open) menu.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [open, activeIndex])

  return <div className={`card-select ${className}`}>
    {showLabel && <span className="card-select-label">{label}</span>}
    <button type="button" ref={trigger} className="card-select-trigger" role="combobox"
      aria-label={label} aria-expanded={open} aria-controls={open ? id : undefined}
      aria-activedescendant={open && activeIndex >= 0 ? `${id}-${activeIndex}` : undefined}
      disabled={!enabled.length} onBlur={close} onKeyDown={handleKey}
      onClick={event => open ? close() : show(event.currentTarget)}>
      <span>{options[selectedIndex]?.label ?? '请选择'}</span>
      <ChevronDown size={15} aria-hidden="true" />
    </button>
    {position && <div className="card-select-menu" id={id} ref={menu} style={position}
      role="listbox" aria-label={label} onMouseDown={event => event.preventDefault()}>
      {options.map((option, index) => <div key={option.value} id={`${id}-${index}`} role="option"
        className={index === activeIndex ? 'card-select-option is-active' : 'card-select-option'}
        aria-selected={option.value === value} aria-disabled={option.disabled || undefined} onClick={() => choose(option)}>
        <span>{option.label}</span>
        {option.value === value && <Check size={15} aria-hidden="true" />}
      </div>)}
    </div>}
  </div>
}
