import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { ErrorNotice, Loading } from '../../components'
import RequestParameterViews from './RequestParameterViews'
import { sources, splitOptions } from './requestOptions'
import { type Preset } from './RequestPresets'

export default function RequestPresetDialog({ presets, pending, applying, removing, error, onClose, onSelect, onApply, onDelete }: {
  presets: { id: string; name: string; preset: Preset }[]
  pending: boolean
  applying: boolean
  removing: boolean
  error: unknown
  onClose: () => void
  onSelect: () => void
  onApply: (preset: Preset) => void
  onDelete: (id: string) => void
}) {
  const titleId = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const [selectedId, setSelectedId] = useState('')
  const selected = presets.find(item => item.id === selectedId) ?? presets[0]
  const preset = selected?.preset
  const busy = applying || removing

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])

  function close() {
    if (busy) return
    dialog.current?.close()
    onClose()
  }

  return createPortal(<dialog ref={dialog} className="panel request-details-dialog preset-dialog" aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); close() }}
    onClick={event => { if (event.target === event.currentTarget) close() }}>
    <header className="section-heading preset-dialog-header">
      <h2 id={titleId}>加载预设</h2>
      <button type="button" className="task-icon-button" aria-label="关闭加载预设" disabled={busy} onClick={close}>
        <X size={18} aria-hidden="true" />
      </button>
    </header>
    {pending ? <Loading /> : preset ? <>
      <div className="preset-dialog-layout">
        <div className="preset-dialog-list" role="group" aria-label="已保存的预设">
          {presets.map(item => <button key={item.id} type="button" aria-pressed={selected.id === item.id}
            disabled={busy} onClick={() => { setSelectedId(item.id); onSelect() }}>
            <strong>{item.name}</strong>
            <span>{item.preset.dataset_id}</span>
          </button>)}
        </div>
        <div className="preset-dialog-preview" key={selected.id}>
          <h3>{selected.name}</h3>
          <dl className="task-details-metadata">
            <div><dt>数据来源</dt><dd>{sources[preset.source]}</dd></div>
            <div><dt>拆分方式</dt><dd>
              {splitOptions.find(option => option.value === preset.split_strategy)?.label ?? preset.split_strategy}
              {preset.split_strategy === 'smart' && preset.split_count ? ` · ${preset.split_count} 份` : ''}
            </dd></div>
            <div><dt>数据集</dt><dd>{preset.dataset_id}</dd></div>
            {preset.source !== 'cds' && <div><dt>镜像目录</dt><dd>{preset.prefix}</dd></div>}
          </dl>
          <RequestParameterViews heading="已保存参数" payload={preset.editor_values} />
        </div>
      </div>
      <footer className="preset-dialog-footer">
        <ErrorNotice error={error} />
        <div className="row-actions">
          <button type="button" className="button danger" disabled={busy} onClick={() => {
            if (window.confirm(`删除预设「${selected.name}」？`)) onDelete(selected.id)
          }}>{removing ? '删除中…' : '删除预设'}</button>
          <button type="button" className="button primary" disabled={busy}
            onClick={() => onApply(preset)}>{applying ? '加载中…' : '加载到表单'}</button>
        </div>
      </footer>
    </> : <div className="request-details-content">
      {error ? <ErrorNotice error={error} /> : <p className="empty-state">还没有保存的预设。</p>}
    </div>}
  </dialog>, document.body)
}
