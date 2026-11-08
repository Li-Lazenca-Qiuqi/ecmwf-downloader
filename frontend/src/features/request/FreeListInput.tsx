import { useEffect, useRef, useState } from 'react'
import { type Field } from '../../lib/api'

export default function FreeListInput({ field, value, onChange }: { field: Field; value: unknown; onChange: (value: unknown) => void }) {
  const valueKey = JSON.stringify(value)
  const lastProduced = useRef(valueKey)
  const [text, setText] = useState(Array.isArray(value) ? value.join(', ') : '')
  useEffect(() => {
    if (valueKey !== lastProduced.current) setText(Array.isArray(value) ? value.join(', ') : '')
    lastProduced.current = valueKey
  }, [valueKey, value])
  return <textarea aria-label={`${field.label} (${field.name})`} placeholder="多个值用逗号或换行分隔" rows={2} value={text} onChange={(event) => {
    const draft = event.target.value
    setText(draft)
    const values = draft.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean).map((item) => {
      if (field.integer || field.item_type === 'number') {
        const number = Number(item)
        return Number.isFinite(number) ? number : item
      }
      if (field.item_type === 'boolean') return item === 'true' ? true : item === 'false' ? false : item
      return item
    })
    const next = values.length ? values : undefined
    // 保留正在键入的分隔符，仅在外部回填时重置输入文本。
    lastProduced.current = JSON.stringify(next)
    onChange(next)
  }} />
}
