import { useMutation } from '@tanstack/react-query'
import { api, type NetworkProxyConfig } from '../../lib/api'
import { ErrorNotice } from '../../components'
import CardSelect from '../../CardSelect'

const modes = [
  { value: 'system', label: '使用系统代理' },
  { value: 'manual', label: '手动代理' },
] as const

type Props = {
  value: NetworkProxyConfig
  testConfig: NetworkProxyConfig
  onChange: (change: Partial<NetworkProxyConfig>) => void
}

export default function NetworkProxySettings({ value, testConfig, onChange }: Props) {
  const test = useMutation({ mutationFn: api.testNetworkProxy })
  const enabled = value.mode !== 'direct'
  const edit = (change: Partial<NetworkProxyConfig>) => {
    test.reset()
    onChange(change)
  }

  return <section className="panel settings-requests network-proxy-settings" aria-labelledby="network-proxy-title">
    <div className="section-heading">
      <h2 id="network-proxy-title">网络代理</h2>
      <label className="ai-enable-control">
        启用
        <input className="settings-switch" type="checkbox" role="switch" aria-label="启用网络代理"
          checked={enabled} disabled={test.isPending}
          onChange={event => edit({ mode: event.target.checked ? 'system' : 'direct' })} />
      </label>
    </div>
    <p className="helper">适用于 CDS、镜像和 AI 服务。</p>
    {enabled && <fieldset className="network-proxy-fields" disabled={test.isPending}>
      <CardSelect label="代理方式" showLabel value={value.mode} options={[...modes]}
        onChange={mode => edit({ mode })} />
      {value.mode === 'manual' && <label>代理地址
        <input type="url" required value={value.url} placeholder="http://主机:端口"
          onChange={event => edit({ url: event.target.value })} />
      </label>}
    </fieldset>}
    <ErrorNotice error={test.error || (test.data && !test.data.ok ? new Error(test.data.message) : null)} />
    <div className="settings-request-actions">
      {test.data?.ok && <span className="helper" role="status">{test.data.message}</span>}
      <button type="button" className="button"
        disabled={test.isPending || (value.mode === 'manual' && !testConfig.url)}
        onClick={() => test.mutate(testConfig)}>
        {test.isPending ? '测试中…' : '测试网络连接'}
      </button>
    </div>
  </section>
}
