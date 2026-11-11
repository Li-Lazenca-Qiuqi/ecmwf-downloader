import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { type Field, type RequestPreviewItem } from '../../lib/api'
import RequestParameterViews from './RequestParameterViews'

export default function RequestDetailsDialog({ datasetId, items, draft, fields, onClose }: {
  datasetId: string
  items: RequestPreviewItem[]
  draft: Record<string, unknown>
  fields: Field[]
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [index, setIndex] = useState(0)
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
      <RequestParameterViews payload={payload} fields={fields} payloadIndex={selectedIndex} />
      {items.length > 1 && <div className="row-actions request-details-navigation">
        <button type="button" className="button" disabled={selectedIndex === 0} onClick={() => setIndex(selectedIndex - 1)}><ChevronLeft size={16} />上一份</button>
        <button type="button" className="button" disabled={selectedIndex === items.length - 1} onClick={() => setIndex(selectedIndex + 1)}>下一份<ChevronRight size={16} /></button>
      </div>}
    </div>
  </dialog>, document.body)
}
