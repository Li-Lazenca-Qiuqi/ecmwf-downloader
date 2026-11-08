import { useMutation } from '@tanstack/react-query'
import { Loader2, RefreshCw } from 'lucide-react'
import { api, type RequestBody } from '../../lib/api'
import { ErrorNotice } from '../../components'

const format = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 3 })

export default function RequestSizePanel({ datasetId, body, ready, disabled, split }: {
  datasetId: string; body: RequestBody; ready: boolean; disabled: boolean; split: string
}) {
  const snapshot = JSON.stringify({ datasetId, request_payload: body.request_payload, schema_revision: body.schema_revision, editor_values: body.editor_values })
  const costing = useMutation({ mutationFn: async (key: string) => {
    const { datasetId: id, ...request } = JSON.parse(key)
    return { key, datasetId: id, result: await api.costing(id, request) }
  } })
  const data = costing.data?.datasetId === datasetId ? costing.data : undefined
  const current = data?.key === snapshot
  const result = data?.result
  const percentage = result?.cost !== undefined && result.limit ? result.cost / result.limit * 100 : undefined
  const exceeded = percentage !== undefined && percentage > 100
  return <section className="panel request-size" aria-label="请求规模">
    <div className="section-heading"><h2>请求规模</h2><span className="size-percentage">{percentage === undefined ? "" : format(percentage) + "%"}</span></div>
    <div className={`size-track ${exceeded ? 'exceeded' : ''} ${data && !current ? 'stale' : ''}`} role="progressbar" aria-label="请求规模占用" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage === undefined ? undefined : Math.min(percentage, 100)} aria-valuetext={data && !current ? '参数已改变，结果待刷新' : percentage === undefined ? '尚未估算' : `${format(percentage)}%`}><span style={{ width: `${Math.min(percentage ?? 0, 100)}%` }} /></div>
    <dl className="size-values"><div><dt>当前规模</dt><dd>{result?.cost === undefined ? '—' : format(result.cost)}</dd></div><div><dt>单次上限</dt><dd>{result?.limit ? format(result.limit) : '—'}</dd></div></dl><button type="button" className="button" aria-label="刷新请求规模" disabled={!ready || disabled || costing.isPending} onClick={() => costing.mutate(snapshot)}>{costing.isPending ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}刷新估算</button>
    <p className="helper">官方规模单位，非字节；参数修改后手动刷新。{result?.source === 'online' && !result.limit && '此数据集未返回可用上限。'}</p>
    {data && !current ? <p className="size-status" role="status">参数已改变，请刷新估算。</p> : current && result?.source === 'online' ? <p className={`size-status ${exceeded ? 'inline-error' : ''}`} role="status">{exceeded ? '超过单次请求上限，请缩小范围或拆分任务。' : '已按当前参数估算。'}</p> : null}
    {split !== 'none' && <p className="helper">显示拆分前的总规模，上限适用于拆分后的每个请求。</p>}
    {result?.error && <p className="inline-error" role="alert">{result.error}</p>}<ErrorNotice error={costing.error} />
  </section>
}
