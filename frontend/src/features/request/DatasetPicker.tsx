import { useId, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../../lib/api'

export default function DatasetPicker({ value, onChange, onSelect, actions, source = 'cds' }: {
  value: string; onChange: (value: string) => void; onSelect: (id: string) => void; actions?: ReactNode; source?: string
}) {
  const id = useId()
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [limit, setLimit] = useState(20)
  const [active, setActive] = useState(-1)
  const catalogue = useQuery({ queryKey: ['datasets', source], queryFn: () => api.datasets(false, source), staleTime: 3600000, retry: false })
  const selected = catalogue.data?.items.find((item) => item.id === value.trim())
  const words = value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  const matches = (catalogue.data?.items || []).filter((item) => words.every((word) => `${item.title} ${item.id}`.toLocaleLowerCase().includes(word)))
  const visible = matches.slice(0, limit)
  const unavailable = catalogue.data?.source === 'error' || catalogue.isError
  const sourceLabel = catalogue.isFetching ? '正在更新目录' : unavailable ? '目录暂不可用' : source !== 'cds' ? '镜像产品目录'
    : catalogue.data?.source === 'cache' ? catalogue.data.stale ? '目录缓存（更新失败）' : '官方目录缓存' : '官方在线目录'
  const select = (datasetId: string) => { onSelect(datasetId); setOpen(false); setEditing(false); setActive(-1) }
  return <div className="dataset-picker" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false); setEditing(false) }}>
    <label htmlFor={id}>数据集</label>
    <div className="dataset-control-row"><div className="dataset-input-anchor"><input id={id} aria-label="数据集" role="combobox" aria-expanded={open} aria-controls={`${id}-options`} aria-autocomplete="list"
      aria-activedescendant={open && active >= 0 && visible[active] ? `${id}-option-${active}` : undefined}
      autoComplete="off" value={editing ? draft : selected?.title || value} title={value} placeholder="搜索数据集名称或 ID，也可直接输入 ID" required
      onFocus={(event) => { setDraft(selected?.title || value); setEditing(true); setOpen(true); event.currentTarget.select() }} onChange={(event) => { setDraft(event.target.value); setEditing(true); onChange(event.target.value); setOpen(true); setLimit(20); setActive(-1) }}
      onKeyDown={(event) => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setOpen(true); setActive((current) => Math.max(0, Math.min(visible.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1)))) }
        if (event.key === 'Escape') { setOpen(false); setActive(-1) }
        if (event.key === 'Enter') { event.preventDefault(); select(open && active >= 0 && visible[active] ? visible[active].id : matches.length === 1 ? matches[0].id : value.trim()) }
      }} />
    {open && <div className="dataset-results">
      <div id={`${id}-options`} role="listbox" aria-label="数据集搜索结果">
        {visible.map((item, index) => <button type="button" role="option" aria-selected={index === active} id={`${id}-option-${index}`} key={item.id}
          onMouseDown={(event) => event.preventDefault()} onClick={() => select(item.id)}><span>{item.title}</span><small>{item.id}</small></button>)}
      </div>
      {!catalogue.isFetching && !matches.length && <p className="helper">{catalogue.data?.items.length ? '没有匹配的数据集，可换用名称关键词或直接输入 ID。' : '暂无可用目录，可直接输入数据集 ID。'}</p>}
      {matches.length > limit && <button type="button" className="button" onClick={() => setLimit((current) => current + 20)}>显示更多（已显示 {visible.length} / {matches.length}）</button>}
    </div>}
    </div>
      <div className="dataset-actions">
        <button type="button" className="button" disabled={catalogue.isFetching} onClick={() => { void client.fetchQuery({ queryKey: ['datasets', source], queryFn: () => api.datasets(true, source), staleTime: 0 }).catch(() => undefined) }}><RefreshCw size={15} className={catalogue.isFetching ? 'spin' : undefined} />刷新目录</button>
        {actions}
      </div>
    </div>
    <div className="dataset-catalogue-status" role="status">
      <span className="catalogue-source" data-state={unavailable || catalogue.data?.stale ? 'warning' : catalogue.isFetching ? 'loading' : catalogue.data?.source}>{sourceLabel}</span>
      {catalogue.data && catalogue.data.source !== 'error' && <span className="catalogue-count">{catalogue.data.catalogue_total} 个数据集</span>}
      {selected && <code className="catalogue-id" title={selected.id}>{selected.id}</code>}
    </div>
    {(catalogue.data?.error || catalogue.isError) && <p className="notice">{catalogue.data?.error || '官方目录请求失败，请重试或手动输入 ID。'}</p>}
  </div>
}
