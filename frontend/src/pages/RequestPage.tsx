import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { api, type RequestBody } from '../lib/api'
import { ErrorNotice } from '../components'

const initialPayload = JSON.stringify({ product_type: ['reanalysis'], variable: ['2m_temperature'], year: ['2024'], month: ['01'], day: ['01'], time: ['00:00'], area: [31, 120, 30, 121], data_format: 'netcdf', download_format: 'unarchived' }, null, 2)
function parsePayload(text: string): Record<string, unknown> {
  let value: unknown
  try { value = JSON.parse(text) } catch { throw new Error('请求参数必须是有效的 JSON，请检查逗号、引号和括号。') }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('请求参数必须是 JSON 对象。')
  return value as Record<string, unknown>
}
export default function RequestPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [datasetId, setDatasetId] = useState('reanalysis-era5-single-levels')
  const [payloadText, setPayloadText] = useState(initialPayload)
  const [split, setSplit] = useState('none')
  const [outputDir, setOutputDir] = useState('')
  const [prompt, setPrompt] = useState('')
  const [showAI, setShowAI] = useState(false)
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: api.datasets })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const schema = useQuery({ queryKey: ['schema', datasetId], queryFn: () => api.schema(datasetId), enabled: showAI && !!datasetId.trim() })
  const body = (): RequestBody => {
    if (!datasetId.trim()) throw new Error('请输入数据集 ID。')
    return { dataset_id: datasetId.trim(), request_payload: parsePayload(payloadText), split_strategy: split, ...(outputDir.trim() ? { output_dir: outputDir.trim() } : {}) }
  }
  const preview = useMutation({ mutationFn: async () => api.preview(body()) })
  const create = useMutation({
    mutationFn: async () => api.createTasks(body()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
      navigate('/tasks')
    },
  })
  const suggestion = useMutation({
    mutationFn: async () => {
      const current = parsePayload(payloadText)
      const result = await api.suggestion({ field_schema: schema.data || {}, user_request: prompt })
      const candidate = result.suggestion.parameters || result.suggestion.request_payload || result.suggestion
      if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) throw new Error('AI 没有返回有效的参数对象。')
      return JSON.stringify({ ...current, ...candidate }, null, 2)
    },
    onSuccess: (text) => { setPayloadText(text); preview.reset(); create.reset() },
  })
  const changed = () => { preview.reset(); create.reset() }
  const busy = create.isPending || preview.isPending || suggestion.isPending
  return <section className="page request-page">
    <div className="page-heading"><div><h1>添加任务</h1><p>填写请求，添加后自动进入下载队列。</p></div></div>
    <form className="panel request-form" onSubmit={(event) => { event.preventDefault(); if (!busy) create.mutate() }}>
      <fieldset disabled={busy}>
        <label>数据集<input list="dataset-options" value={datasetId} onChange={(event) => { setDatasetId(event.target.value); changed() }} required placeholder="输入 CDS 数据集 ID" /></label>
        <datalist id="dataset-options">{datasets.data?.items.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.title}</option>)}</datalist>
        <label>请求参数（JSON）<textarea className="payload-editor" rows={16} value={payloadText} onChange={(event) => { setPayloadText(event.target.value); changed() }} spellCheck={false} required /></label>
        <p className="helper">可以粘贴 CDS 页面导出的请求参数，保留数组、数字等原始类型。</p>
        <details className="advanced"><summary>输出与拆分</summary><div className="form-grid">
          <label>输出目录<input value={outputDir} onChange={(event) => { setOutputDir(event.target.value); changed() }} placeholder={settings.data?.download.output_dir || '使用后台配置的目录'} /></label>
          <label>拆分方式<select value={split} onChange={(event) => { setSplit(event.target.value); changed() }}><option value="none">不拆分</option><option value="year">按年</option><option value="month">按年月</option></select></label>
        </div><p className="helper">目录位于运行后台服务的机器上。拆分只按请求中的数据日期生成多个任务。</p></details>
        <details className="advanced" onToggle={(event) => setShowAI(event.currentTarget.open)}><summary>AI 参数建议（可选）</summary>
          <p className="helper">需要预先配置 AI 服务，建议生成后请检查参数。</p>
          <label>需求描述<textarea rows={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} /></label>
          <button type="button" className="button" disabled={!prompt.trim() || schema.isPending || !!schema.error || !settings.data?.ai.enabled} onClick={() => suggestion.mutate()}>{suggestion.isPending ? '生成中…' : '生成建议'}</button>
          {settings.data && !settings.data.ai.enabled && <p className="helper">AI 服务尚未启用，可通过 CLI 配置。</p>}
          <ErrorNotice error={schema.error || suggestion.error} />
        </details>
      </fieldset>
      <ErrorNotice error={preview.error || create.error} />
      {preview.data && <div className="notice preview-result"><strong>本地预览：将添加 {preview.data.items.length} 个任务</strong><ul>{preview.data.items.map((item, index) => <li key={index}>{item.output_path}</li>)}</ul><p>预览不会创建任务，也不代表 CDS 已接受请求。</p></div>}
      <div className="form-actions"><Link className="button" to="/tasks">返回队列</Link><div className="row-actions"><button type="button" className="button" disabled={busy} onClick={() => preview.mutate()}>预览</button><button className="button primary" type="submit" disabled={busy}>{create.isPending ? <Loader2 size={16} className="spin" /> : <Download size={16} />}添加并下载</button></div></div>
    </form>
  </section>
}
