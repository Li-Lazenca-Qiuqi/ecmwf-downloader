import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ErrorNotice, Loading } from '../components'

export default function SettingsPage() {
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  return <section className="page settings-page"><div className="page-heading"><div><h1>设置</h1><p>当前后台配置，可通过 CLI 修改。运行中的调度器参数需重启服务后生效。</p></div></div>
    <ErrorNotice error={settings.error} />{settings.isPending ? <Loading /> : settings.data && <dl className="panel settings-list">
      <dt>下载目录</dt><dd>{settings.data.download.output_dir}</dd>
      <dt>最大并发</dt><dd>{settings.data.download.max_workers}</dd>
      <dt>失败重试上限</dt><dd>{settings.data.download.max_retries} 次</dd>
      <dt>重试等待</dt><dd>{settings.data.download.retry_delays.join(' / ')} 秒</dd>
      <dt>数据库</dt><dd>{settings.data.database_path}</dd>
      <dt>AI 参数建议</dt><dd>{settings.data.ai.enabled ? `已启用${settings.data.ai.model ? ` · ${settings.data.ai.model}` : ''}` : '未启用'}</dd>
    </dl>}
  </section>
}
