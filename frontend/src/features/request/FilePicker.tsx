import { useState } from 'react'
import { type Field } from '../../lib/api'
import CommaOptionInput from './CommaOptionInput'

export default function FilePicker({ field, value, onChange }: { field: Field; value: unknown; onChange: (value: unknown) => void }) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(0)
  const selected = Array.isArray(value) ? value : []
  const options = field.options.filter((option) => `${option.label} ${option.value}`.toLowerCase().includes(query.toLowerCase()))
  const pages = Math.max(1, Math.ceil(options.length / 40))
  const toggle = (key: unknown, checked: boolean) => { const values = checked ? [...new Set([...selected, key])] : selected.filter((item) => item !== key); onChange(values.length ? values : undefined) }
  return <div className="file-picker"><CommaOptionInput field={{ ...field, options: field.options.map((option) => ({ ...option, label: String(option.value).split('/').at(-1)! })) }} value={value} onChange={onChange} multiple onSearch={(text) => { setQuery(text); setPage(0) }} /><div className="option-tools"><span>已选 {selected.length} / {field.options.length}</span><button type="button" className="text-button" onClick={() => onChange([...new Set([...selected, ...options.map((option) => option.value)])])}>全选匹配结果（{options.length}）</button><button type="button" className="text-button" onClick={() => onChange(undefined)}>清空</button></div><div className="file-table-scroll"><table className="file-options"><thead><tr><th scope="col">选择</th><th scope="col">文件名</th><th scope="col">大小</th></tr></thead><tbody>{options.slice(page * 40, (page + 1) * 40).map((option) => {
    const size = option.label.match(/ \(([^()]*)\)$/)?.[1]
    const name = String(option.value).split('/').at(-1)
    return <tr key={String(option.value)} className={selected.includes(option.value) ? 'selected' : ''}><td><input type="checkbox" aria-label={`选择 ${name}`} checked={selected.includes(option.value)} onChange={(event) => toggle(option.value, event.target.checked)} /></td><td title={String(option.value)}>{name}</td><td>{size || '未知'}</td></tr>
  })}</tbody></table>{!options.length && <p className="helper">没有匹配的文件。</p>}</div><div className="file-pagination"><button type="button" className="button" disabled={!page} onClick={() => setPage(page - 1)}>上一页</button><span>{page + 1} / {pages} 页 · 匹配 {options.length} 项</span><button type="button" className="button" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>下一页</button></div></div>
}
