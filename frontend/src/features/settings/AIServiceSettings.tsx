import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Radio, Sparkles } from 'lucide-react'
import { api, type AIConfigInput } from '../../lib/api'
import { ErrorNotice, Loading } from '../../components'

export default function AIServiceSettings() {
  const client = useQueryClient()
  const configQuery = useQuery({ queryKey: ['ai-config'], queryFn: api.aiConfig, staleTime: 30000, retry: false })
  const config = configQuery.data
  const [urlDraft, setUrlDraft] = useState<string>()
  const [modelDraft, setModelDraft] = useState<string>()
  const [key, setKey] = useState('')
  const url = urlDraft ?? (config?.base_url || 'https://api.openai.com/v1')
  const model = modelDraft ?? config?.model ?? ''

  const save = useMutation({
    mutationFn: ({ body }: { body: AIConfigInput; source: 'form' | 'switch' }) => api.saveAIConfig(body),
    onSuccess: (result, { source }) => {
      client.setQueryData(['ai-config'], result)
      void client.invalidateQueries({ queryKey: ['settings'] })
      if (source === 'form') {
        setUrlDraft(undefined)
        setModelDraft(undefined)
        setKey('')
      }
    },
  })
  const test = useMutation({ mutationFn: api.testAIConfig })
  const body: AIConfigInput = {
    enabled: config?.enabled ?? false, base_url: url.trim(), model: model.trim(), json_mode: config?.json_mode ?? true,
    ...(key.trim() ? { api_key: key.trim() } : {}),
  }
  const working = save.isPending || test.isPending
  const savedKeyMatches = config?.has_api_key && body.base_url.replace(/\/+$/, '') === config.base_url
  const canTest = body.base_url && body.model && (body.api_key || savedKeyMatches)

  const saveSwitch = (change: Partial<Pick<AIConfigInput, 'enabled' | 'json_mode'>>) => {
    if (!config) return
    const { enabled, json_mode, base_url, model } = config
    test.reset()
    save.mutate({ body: { enabled, json_mode, base_url, model, ...change }, source: 'switch' })
  }

  return <section className="panel settings-ai" id="ai" aria-labelledby="settings-ai-title">
    <div className="settings-ai-heading">
      <div className="ai-service-heading">
        <span className="ai-service-icon"><Sparkles size={18} aria-hidden="true" /></span>
        <div><h2 id="settings-ai-title">AI 服务</h2><p id="ai-enabled-help" className="helper">为提交请求页提供参数补全。</p></div>
      </div>
      {config && <label className="ai-enable-control">
        启用
        <input className="ai-config-switch" type="checkbox" role="switch" aria-label="启用 AI 参数补全"
          aria-describedby="ai-enabled-help" checked={config.enabled} disabled={working}
          onChange={event => saveSwitch({ enabled: event.target.checked })} />
      </label>}
    </div>
    <ErrorNotice error={configQuery.error} />
    {configQuery.isPending ? <Loading /> : <form onSubmit={event => {
      event.preventDefault()
      if (!working) {
        test.reset()
        save.mutate({ body, source: 'form' })
      }
    }}>
      <fieldset className="ai-config-fields" disabled={working} onChange={() => { test.reset(); save.reset() }}>
        <label>服务地址<input aria-label="AI 服务地址" type="url" value={url} onChange={event => setUrlDraft(event.target.value)} placeholder="https://api.openai.com/v1" required /></label>
        <label>模型名称<input aria-label="AI 模型名称" value={model} onChange={event => setModelDraft(event.target.value)} placeholder="填写服务支持的模型 ID" required /></label>
        <label className="ai-config-key">API Key<input aria-label="AI API Key" type="text" autoComplete="off" spellCheck={false} autoCapitalize="off"
          value={key} onChange={event => setKey(event.target.value)}
          placeholder={savedKeyMatches ? '已保存，留空复用' : '输入 API Key'} required={config?.enabled && !config.has_api_key} /></label>
      </fieldset>
      {config && <label className="ai-json-control">
        <span>使用 JSON 模式<small id="ai-json-help">默认开启，要求服务返回 JSON 对象。</small></span>
        <input className="ai-config-switch" type="checkbox" role="switch" aria-describedby="ai-json-help"
          checked={config.json_mode} disabled={working} onChange={event => saveSwitch({ json_mode: event.target.checked })} />
      </label>}
      <ErrorNotice error={save.error || test.error} />
      {test.data && <p className="notice" role="status">{test.data.message}</p>}
      {save.isSuccess && save.variables.source === 'form' && <p className="notice" role="status">AI 服务配置已保存。</p>}
      <div className="ai-config-actions">
        <button type="button" className="button" disabled={working || !canTest} onClick={() => { save.reset(); test.mutate(body) }}>
          {test.isPending ? <Loader2 size={15} className="spin" /> : <Radio size={15} />}测试连接
        </button>
        <button type="submit" className="button primary" disabled={working}>
          {save.isPending && save.variables.source === 'form' && <Loader2 size={15} className="spin" />}保存配置
        </button>
      </div>
    </form>}
  </section>
}
