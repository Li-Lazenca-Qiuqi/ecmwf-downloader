import { useMutation } from '@tanstack/react-query'
import { Loader2, Radio, Sparkles } from 'lucide-react'
import { api, type AIConfigInput, type NetworkProxyConfig, type ReasoningEffort } from '../../lib/api'
import { ErrorNotice } from '../../components'
import CardSelect from '../../CardSelect'

const effortLabels: Record<ReasoningEffort, string> = {
  default: 'Service Default',
  none: 'None',
  minimal: 'Minimal',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  xhigh: 'XHigh',
  max: 'Max',
}

type Props = {
  value: AIConfigInput
  network: NetworkProxyConfig
  efforts: readonly ReasoningEffort[]
  onChange: (change: Partial<AIConfigInput>) => void
}

export default function AIServiceSettings({ value, network, efforts, onChange }: Props) {
  const body = {
    enabled: value.enabled,
    base_url: value.base_url.trim(),
    model: value.model.trim(),
    api_key: value.api_key?.trim(),
    json_mode: value.json_mode,
    reasoning_effort: value.reasoning_effort,
    network_proxy: network,
  }
  const test = useMutation({ mutationFn: () => api.testAIConfig(body), gcTime: 0 })
  const canTest = body.base_url && body.model && body.api_key
    && (network.mode !== 'manual' || !!network.url)

  const edit = (change: Partial<AIConfigInput>) => {
    test.reset()
    onChange(change)
  }

  return <section className="panel settings-ai" id="ai" aria-labelledby="settings-ai-title">
    <div className="settings-ai-heading">
      <div className="ai-service-heading">
        <span className="ai-service-icon"><Sparkles size={18} aria-hidden="true" /></span>
        <div><h2 id="settings-ai-title">AI 服务</h2><p id="ai-enabled-help" className="helper">为提交请求页提供参数补全。</p></div>
      </div>
      <label className="ai-enable-control">
        启用
        <input className="settings-switch" type="checkbox" role="switch" aria-label="启用 AI 参数补全"
          aria-describedby="ai-enabled-help" checked={value.enabled} disabled={test.isPending}
          onChange={event => edit({ enabled: event.target.checked })} />
      </label>
    </div>
    <fieldset className="ai-config-fields" disabled={test.isPending}>
      <label>服务地址<input aria-label="AI 服务地址" type="url" value={value.base_url}
        onChange={event => edit({ base_url: event.target.value })} placeholder="https://api.openai.com/v1" required /></label>
      <label>模型名称<input aria-label="AI 模型名称" value={value.model}
        onChange={event => edit({ model: event.target.value })} placeholder="填写服务支持的模型 ID" required /></label>
      <CardSelect label="Reasoning Effort" showLabel value={value.reasoning_effort}
        options={(['default', ...efforts] as const).map(option => ({ value: option, label: effortLabels[option] }))}
        onChange={reasoning_effort => edit({ reasoning_effort })} />
      <div className="ai-config-key">
        <label htmlFor="settings-ai-key">API Key</label>
        <div className="ai-key-controls">
          <input id="settings-ai-key" aria-label="AI API Key" type="text" autoComplete="off" spellCheck={false} autoCapitalize="off"
            value={value.api_key ?? ''} onChange={event => edit({ api_key: event.target.value })}
            placeholder="输入 API Key" required={value.enabled} />
          <button type="button" className="button" disabled={test.isPending || !canTest} onClick={() => test.mutate()}>
            {test.isPending ? <Loader2 size={15} className="spin" /> : <Radio size={15} />}测试连接
          </button>
        </div>
      </div>
    </fieldset>
    <label className="ai-json-control">
      <span>使用 JSON 模式<small id="ai-json-help">默认开启，要求服务返回 JSON 对象。</small></span>
      <input className="settings-switch" type="checkbox" role="switch" aria-describedby="ai-json-help"
        checked={value.json_mode} disabled={test.isPending} onChange={event => edit({ json_mode: event.target.checked })} />
    </label>
    <ErrorNotice error={test.error} />
    {test.data && <p className="notice" role="status">{test.data.message}</p>}
  </section>
}
