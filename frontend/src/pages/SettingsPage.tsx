import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ErrorNotice, Loading } from '../components'
import AIServiceSettings from '../features/settings/AIServiceSettings'

export default function SettingsPage() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const current = settings.data?.requests
  const [pollDraft, setPollDraft] = useState<string>()
  const [retriesDraft, setRetriesDraft] = useState<string>()
  const pollInterval = pollDraft ?? String(current?.poll_interval ?? '')
  const maxRetries = retriesDraft ?? String(current?.max_retries ?? '')
  const changes = {
    ...(pollDraft !== undefined && Number(pollInterval) !== current?.poll_interval ? { poll_interval: Number(pollInterval) } : {}),
    ...(retriesDraft !== undefined && Number(maxRetries) !== current?.max_retries ? { max_retries: Number(maxRetries) } : {}),
  }
  const dirty = Object.keys(changes).length > 0
  const save = useMutation({
    mutationFn: api.saveRequestSettings,
    onSuccess: result => {
      client.setQueryData(['settings'], result)
      setPollDraft(undefined)
      setRetriesDraft(undefined)
    },
  })

  return <section className="page settings-page">
    <div className="page-heading"><div><h1>设置</h1><p>配置 AI 服务和请求监视。</p></div></div>
    <AIServiceSettings />
    <section className="panel settings-requests" aria-labelledby="settings-requests-title">
      <h2 id="settings-requests-title">请求监视</h2>
      <ErrorNotice error={settings.error || save.error} />
      {settings.isPending ? <Loading /> : current && <form onSubmit={event => {
        event.preventDefault()
        if (dirty && !save.isPending) save.mutate(changes)
      }}>
        <fieldset className="settings-request-fields" disabled={save.isPending} onChange={() => save.reset()}>
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
        </fieldset>
        <div className="settings-request-actions">
          <button type="submit" className="button primary" disabled={save.isPending || !dirty}>
            {save.isPending ? '保存中…' : '保存监视设置'}
          </button>
          {save.isSuccess && <span className="helper" role="status">监视设置已保存。</span>}
        </div>
      </form>}
    </section>
  </section>
}
