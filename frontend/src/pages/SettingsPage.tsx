import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type AIConfigInput, type NetworkProxyConfig, type SettingsUpdate } from '../lib/api'
import { ErrorNotice, Loading } from '../components'
import AIServiceSettings from '../features/settings/AIServiceSettings'
import NetworkProxySettings from '../features/settings/NetworkProxySettings'

export default function SettingsPage() {
  const query = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const key = useQuery({
    queryKey: ['settings', 'ai-key'],
    queryFn: ({ signal }) => api.settingsAIKey(signal),
    gcTime: 0, retry: false,
  })
  return <section className="page settings-page">
    {(query.isPending || key.isPending) && <Loading />}
    <ErrorNotice error={query.error || key.error} />
    {query.data && key.data && <SettingsForm current={query.data} savedAIKey={key.data.api_key} />}
  </section>
}

function SettingsForm({ current, savedAIKey }: { current: Awaited<ReturnType<typeof api.settings>>; savedAIKey: string }) {
  const client = useQueryClient()
  const [proxyDraft, setProxyDraft] = useState<Partial<NetworkProxyConfig>>({})
  const [aiDraft, setAIDraft] = useState<Partial<AIConfigInput>>({})
  const [pollDraft, setPollDraft] = useState<string>()
  const [retriesDraft, setRetriesDraft] = useState<string>()
  const proxy = { ...current.network_proxy, ...proxyDraft }
  const network = { mode: proxy.mode, url: proxy.mode === 'manual' ? proxy.url.trim() : current.network_proxy.url }
  const ai = { ...current.ai_config, api_key: savedAIKey, ...aiDraft }
  const aiKey = ai.api_key?.trim() ?? ''
  const aiKeyChanged = aiKey !== savedAIKey
  const pollInterval = pollDraft ?? String(current.requests.poll_interval)
  const maxRetries = retriesDraft ?? String(current.requests.max_retries)
  const monitoring = {
    ...(pollDraft !== undefined && Number(pollDraft) !== current.requests.poll_interval ? { poll_interval: Number(pollDraft) } : {}),
    ...(retriesDraft !== undefined && Number(retriesDraft) !== current.requests.max_retries ? { max_retries: Number(retriesDraft) } : {}),
  }
  const aiChanges = {
    ...(ai.enabled !== current.ai_config.enabled ? { enabled: ai.enabled } : {}),
    ...(ai.base_url.trim() !== current.ai_config.base_url ? { base_url: ai.base_url.trim() } : {}),
    ...(ai.model.trim() !== current.ai_config.model ? { model: ai.model.trim() } : {}),
    ...(ai.json_mode !== current.ai_config.json_mode ? { json_mode: ai.json_mode } : {}),
  }
  const proxyChanged = network.mode !== current.network_proxy.mode || network.url !== current.network_proxy.url
  const changes: SettingsUpdate = {
    ...(proxyChanged ? { network_proxy: network } : {}),
    ...(Object.keys(aiChanges).length ? { ai: aiChanges } : {}),
    ...(Object.keys(monitoring).length ? { requests: monitoring } : {}),
  }
  const dirty = Object.keys(changes).length > 0 || aiKeyChanged
  const save = useMutation({
    mutationFn: (values: SettingsUpdate) => api.saveSettings(values, aiKeyChanged ? aiKey : undefined),
    onSuccess: (result, values) => {
      if (aiKeyChanged) client.setQueryData(['settings', 'ai-key'], { api_key: aiKey })
      client.setQueryData(['settings'], result)
      client.setQueryData(['ai-config'], result.ai_config)
      setProxyDraft({})
      setAIDraft({})
      setPollDraft(undefined)
      setRetriesDraft(undefined)
      if (values.network_proxy) {
        void client.invalidateQueries({ queryKey: ['datasets'] })
        void client.invalidateQueries({ queryKey: ['request-schema'] })
        void client.invalidateQueries({ queryKey: ['request-constraints'] })
      }
    },
  })

  return <form onSubmit={event => {
    event.preventDefault()
    if (dirty && !save.isPending) save.mutate(changes)
  }} onChange={() => save.reset()}>
    <div className="page-heading">
      <div><h1>设置</h1><p>配置网络代理、AI 服务和请求监视。</p></div>
      <button type="submit" className="button primary" disabled={!dirty || save.isPending}>
        {save.isPending ? '保存中…' : '保存配置'}
      </button>
    </div>
    <ErrorNotice error={save.error} />
    {save.isSuccess && <p className="notice" role="status">配置已保存。</p>}
    <fieldset disabled={save.isPending}>
      <NetworkProxySettings value={proxy} testConfig={network}
        onChange={change => { save.reset(); setProxyDraft(draft => ({ ...draft, ...change })) }} />
      <AIServiceSettings value={ai} network={network}
        onChange={change => setAIDraft(draft => ({ ...draft, ...change }))} />
      <section className="panel settings-requests" aria-labelledby="settings-requests-title">
        <h2 id="settings-requests-title">请求监视</h2>
        <div className="settings-request-fields">
          <div>
            <label>状态查询间隔（秒）
              <input type="number" min={1} max={3600} step="any" required value={pollInterval}
                aria-describedby="poll-interval-help" onChange={event => setPollDraft(event.target.value)} />
            </label>
            <p className="helper" id="poll-interval-help">保存后用于下一次安排的状态查询。</p>
          </div>
          <div>
            <label>查询重试上限（次）
              <input type="number" min={0} max={20} step={1} required value={maxRetries}
                aria-describedby="max-retries-help" onChange={event => setRetriesDraft(event.target.value)} />
            </label>
            <p className="helper" id="max-retries-help">新请求查询失败后最多重试的次数。设为 0 时不自动重试。</p>
          </div>
        </div>
      </section>
    </fieldset>
  </form>
}
