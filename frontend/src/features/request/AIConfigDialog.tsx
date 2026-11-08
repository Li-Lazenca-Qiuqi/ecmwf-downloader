import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, X } from 'lucide-react'
import { api, type AIConfig } from '../../lib/api'
import { ErrorNotice } from '../../components'

export default function AIConfigDialog({ config, onClose }: { config?: AIConfig; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const client = useQueryClient()
  const [enabled, setEnabled] = useState(config?.enabled || !config?.has_api_key)
  const [url, setUrl] = useState(config?.base_url || 'https://api.openai.com/v1')
  const [model, setModel] = useState(config?.model || 'gpt-4o-mini')
  const [key, setKey] = useState('')
  const [jsonMode, setJsonMode] = useState(config?.json_mode ?? true)
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close() }, [])
  const save = useMutation({
    mutationFn: () => api.saveAIConfig({ enabled, base_url: url.trim(), model: model.trim(), json_mode: jsonMode, ...(key.trim() ? { api_key: key.trim() } : {}) }),
    onSuccess: (result) => { client.setQueryData(['ai-config'], result); void client.invalidateQueries({ queryKey: ['settings'] }); setKey(''); onClose() },
  })
  return createPortal(<dialog ref={dialog} className="ai-config-dialog" aria-labelledby="ai-config-title" onCancel={(event) => { event.preventDefault(); if (!save.isPending) onClose() }}>
    <div className="ai-config-heading"><div><h2 id="ai-config-title">AI 服务配置</h2><p className="helper">使用支持 OpenAI Chat Completions 的服务。</p></div><button type="button" className="icon-button" aria-label="关闭 AI 配置" disabled={save.isPending} onClick={onClose}><X size={18} /></button></div>
    <form onSubmit={(event) => { event.preventDefault(); if (!save.isPending) save.mutate() }}>
      <fieldset disabled={save.isPending}>
        <label>服务地址<input aria-label="AI 服务地址" type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://api.openai.com/v1" required autoFocus /></label>
        <label>模型名称<input aria-label="AI 模型名称" value={model} onChange={(event) => setModel(event.target.value)} placeholder="填写服务支持的模型 ID" required /></label>
        <label>API Key<input aria-label="AI API Key" type="password" autoComplete="new-password" value={key} onChange={(event) => setKey(event.target.value)} placeholder={config?.has_api_key ? '已保存，留空保留原密钥' : '输入 API Key'} required={enabled && !config?.has_api_key} /></label>
        <p className="helper">密钥仅保存在后端凭据文件中，保存后不回显。</p>
        <label className="option"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />启用 AI 参数补全</label>
        <label className="option"><input type="checkbox" checked={jsonMode} onChange={(event) => setJsonMode(event.target.checked)} />使用 JSON 模式</label>
        <p className="helper">如果兼容服务不支持 JSON 模式，可关闭后重试。</p>
      </fieldset>
      <ErrorNotice error={save.error} />
      <div className="ai-config-actions"><button type="button" className="button" disabled={save.isPending} onClick={onClose}>取消</button><button type="submit" className="button primary" disabled={save.isPending}>{save.isPending && <Loader2 size={15} className="spin" />}保存配置</button></div>
    </form>
  </dialog>, document.body)
}
