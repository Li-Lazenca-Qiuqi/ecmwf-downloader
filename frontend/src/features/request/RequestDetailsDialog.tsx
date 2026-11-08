import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { type Field, type RequestPreviewItem } from '../../lib/api'
import RequestPreviewCode from './RequestPreviewCode'

function ParameterValue({ value, field }: { value: unknown; field?: Field }) {
  const labels = new Map<unknown, string>(field?.options.map(option => [option.value, option.label]))
  const format = (entry: unknown) => labels.get(entry) ?? (typeof entry === 'boolean' ? (entry ? '是' : '否') : String(entry ?? '空值'))

  if (Array.isArray(value)) {
    if (!value.length) return <span>空列表</span>
    if (field?.field_type === 'area' && value.length === 4) {
      return <dl className="request-parameter-properties">{['北界', '西界', '南界', '东界'].map((label, i) => <div key={label}><dt>{label}</dt><dd>{format(value[i])}</dd></div>)}</dl>
    }
    return <ul className="request-parameter-values">{value.map((entry, i) => <li key={i}>
      {entry !== null && typeof entry === 'object' ? <ParameterValue value={entry} /> : format(entry)}
    </li>)}</ul>
  }
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value)
    if (!entries.length) return <span>无子参数</span>
    return <dl className="request-parameter-properties">{entries.map(([name, entry]) => <div key={name}>
      <dt>{field?.properties?.[name]?.label ?? name}</dt>
      <dd><ParameterValue value={entry} field={field?.properties?.[name]} /></dd>
    </div>)}</dl>
  }
  return <span>{format(value)}</span>
}

function RequestParameterCards({ payload, fields }: { payload: Record<string, unknown>; fields: Field[] }) {
  const entries = Object.entries(payload)
  const definitions = new Map(fields.map(field => [field.name, field]))
  if (!entries.length) return <p className="helper">尚未选择请求参数。</p>

  return <dl className="request-parameter-cards" aria-label="已选请求参数">
    {entries.map(([name, value]) => {
      const field = definitions.get(name)
      return <div className="request-parameter-card" key={name}>
        <dt>{field?.label ?? name}{field?.label && field.label !== name && <code>{name}</code>}</dt>
        <dd><ParameterValue value={value} field={field} /></dd>
      </div>
    })}
  </dl>
}

export default function RequestDetailsDialog({ datasetId, items, draft, fields, onClose }: {
  datasetId: string
  items: RequestPreviewItem[]
  draft: Record<string, unknown>
  fields: Field[]
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [index, setIndex] = useState(0)
  const [view, setView] = useState<'cards' | 'json'>('cards')
  const selectedIndex = Math.min(index, Math.max(0, items.length - 1))
  const item = items[selectedIndex]
  const payload = item?.request_payload ?? draft

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])

  function close() {
    dialog.current?.close()
    onClose()
  }

  return createPortal(<dialog ref={dialog} className="panel request-details-dialog" aria-labelledby="request-details-title"
    onCancel={event => { event.preventDefault(); close() }}
    onClick={event => { if (event.target === event.currentTarget) close() }}>
    <div className="request-details-content">
      <div className="section-heading">
        <h2 id="request-details-title">请求详情</h2>
        <button type="button" className="task-icon-button" onClick={close} aria-label="关闭请求详情" title="关闭请求详情"><X size={18} aria-hidden="true" /></button>
      </div>
      <div className="request-details-meta" aria-live="polite">
        <strong>{item ? `第 ${selectedIndex + 1} / ${items.length} 个请求` : '当前参数草稿'}</strong>
        <span>{datasetId}</span>
        {item ? item.label !== datasetId && <span>{item.label}</span> : <span>参数有效后可查看每个计划请求。</span>}
      </div>
      <div className="row-actions request-details-views" role="group" aria-label="参数视图">
        <button type="button" className="button" aria-pressed={view === 'cards'} onClick={() => setView('cards')}>卡片视图</button>
        <button type="button" className="button" aria-pressed={view === 'json'} onClick={() => setView('json')}>JSON</button>
      </div>
      {view === 'cards'
        ? <RequestParameterCards key={selectedIndex} payload={payload} fields={fields} />
        : <RequestPreviewCode key={selectedIndex} payload={payload} />}
      {items.length > 1 && <div className="row-actions request-details-navigation">
        <button type="button" className="button" disabled={selectedIndex === 0} onClick={() => setIndex(selectedIndex - 1)}><ChevronLeft size={16} />上一份</button>
        <button type="button" className="button" disabled={selectedIndex === items.length - 1} onClick={() => setIndex(selectedIndex + 1)}>下一份<ChevronRight size={16} /></button>
      </div>}
    </div>
  </dialog>, document.body)
}
