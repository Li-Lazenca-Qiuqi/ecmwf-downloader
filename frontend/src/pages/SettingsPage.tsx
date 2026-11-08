import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Settings2 } from 'lucide-react'
import { api } from '../lib/api'
import { ErrorNotice, Loading } from '../components'
import AIConfigDialog from '../features/request/AIConfigDialog'

export default function SettingsPage() {
  const [configure, setConfigure] = useState(false)
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const ai = useQuery({ queryKey: ['ai-config'], queryFn: api.aiConfig, staleTime: 30000, retry: false })
  return <section className="page settings-page"><div className="page-heading"><div><h1>设置</h1><p>配置 AI 服务并查看后台设置。通过 CLI 保存的调度参数在服务重启后生效。通过本服务 API 更新时，后续调度使用新值，已开始的操作和已安排的重试照常进行。</p></div></div>
    <section className="panel settings-ai" id="ai" aria-labelledby="settings-ai-title">
      <div className="settings-ai-heading"><div><h2 id="settings-ai-title">AI 服务</h2><p className="helper">配置后，在添加任务页面使用参数补全。</p></div><button type="button" className="button" disabled={ai.isPending} onClick={() => setConfigure(true)}><Settings2 size={15} />配置服务</button></div>
      <ErrorNotice error={ai.error} />{ai.isPending ? <Loading /> : ai.data && <dl className="settings-ai-details">
        <dt>状态</dt><dd>{ai.data.ready ? '已就绪' : ai.data.enabled ? ai.data.sdk_available ? '缺少 API Key' : '缺少运行依赖' : '未启用'}</dd>
        <dt>服务地址</dt><dd>{ai.data.base_url}</dd><dt>模型</dt><dd>{ai.data.model}</dd>
        <dt>API Key</dt><dd>{ai.data.has_api_key ? '已保存' : '未配置'}</dd>
      </dl>}
    </section>
    <ErrorNotice error={settings.error} />{settings.isPending ? <Loading /> : settings.data && <dl className="panel settings-list">
      <dt>最大并行 API 操作</dt><dd>{settings.data.requests.max_workers}</dd>
      <dt>查询重试上限</dt><dd>{settings.data.requests.max_retries} 次</dd>
      <dt>状态查询间隔</dt><dd>{settings.data.requests.poll_interval} 秒</dd>
      <dt>重试等待</dt><dd>{settings.data.requests.retry_delays.join(' / ')} 秒</dd>
      <dt>数据库</dt><dd>{settings.data.database_path}</dd>
    </dl>}
    {configure && <AIConfigDialog config={ai.data} onClose={() => setConfigure(false)} />}
  </section>
}
