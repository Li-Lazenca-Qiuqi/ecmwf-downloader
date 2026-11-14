import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUp, Loader2 } from 'lucide-react'
import { api } from '../../lib/api'
import { ErrorNotice } from '../../components'

export default function AIParameterPanel({ ready, pending, error, notice, onEdit, onGenerate }: {
  ready: boolean; pending: boolean; error: unknown; notice: string
  onEdit: () => void; onGenerate: (prompt: string) => void
}) {
  const [prompt, setPrompt] = useState('')
  const config = useQuery({ queryKey: ['ai-config'], queryFn: api.aiConfig, staleTime: 30000, retry: false })
  const enabled = ready && !!prompt.trim() && !pending && !!config.data?.ready
  const generate = () => { if (enabled) onGenerate(prompt.trim()) }
  return <section className="panel ai-parameters" aria-label="AI 补全参数"><h2>AI 补全参数</h2>
    <div className="ai-input-wrap" title={!config.isPending && !config.data?.ready ? '请在设置中配置并启用 AI 服务' : undefined}>
      <textarea aria-label="AI 需求描述" rows={3} maxLength={12000} value={prompt} onChange={(event) => { setPrompt(event.target.value); onEdit() }} placeholder="描述你需要的数据、时间和区域…" onKeyDown={(event) => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); generate() } }} />
      <button type="button" className="button primary ai-send" aria-label="补全参数" aria-keyshortcuts="Control+Enter Meta+Enter" title="补全参数 · Ctrl / ⌘ + Enter" disabled={!enabled} onClick={generate}>{pending ? <Loader2 size={18} className="spin" /> : <ArrowUp size={19} />}</button>
    </div>
    <ErrorNotice error={config.error || error} />
    {notice && <div className="ai-result-notice" role="status">{notice}</div>}
  </section>
}
