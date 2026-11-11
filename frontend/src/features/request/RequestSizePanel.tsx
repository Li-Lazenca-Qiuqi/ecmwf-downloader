import { useMutation } from '@tanstack/react-query'
import { Loader2, RefreshCw } from 'lucide-react'
import { api, type RequestBody } from '../../lib/api'
import { ErrorNotice } from '../../components'

const format = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 3 })
const cdsRequestGuide = 'https://confluence.ecmwf.int/spaces/CKB/pages/174856258/Climate%2BData%2BStore%2BCDS%2Bdocumentation'

export default function RequestSizePanel({ body, ready, disabled }: {
  body: RequestBody; ready: boolean; disabled: boolean
}) {
  const snapshot = JSON.stringify(body)
  const costing = useMutation({ mutationFn: async (key: string) => {
    const { dataset_id: id, ...request } = JSON.parse(key) as RequestBody
    return { key, datasetId: id, result: await api.costing(id, request) }
  } })
  const data = costing.data?.datasetId === body.dataset_id ? costing.data : undefined
  const current = data?.key === snapshot
  const result = data?.result
  const percentage = result?.cost !== undefined && result.limit ? result.cost / result.limit * 100 : undefined
  const band = percentage === undefined ? '' : percentage >= 75 ? 'high' : percentage >= 50 ? 'elevated' : ''
  const exceeded = (result?.over_limit_count ?? 0) > 0
    || (result?.cost !== undefined && result.limit != null && result.cost > result.limit)
  const split = body.split_strategy !== 'none'
  return <section className="request-size" aria-label="请求规模">
    <div className="section-heading"><h3>请求规模</h3><span className="size-percentage">{percentage === undefined ? "" : format(percentage) + "%"}</span></div>
    <div className={`size-track ${band} ${data && !current ? 'stale' : ''}`} role="progressbar" aria-label="请求规模占用" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage === undefined ? undefined : Math.min(percentage, 100)} aria-valuetext={data && !current ? '参数已改变，结果待刷新' : percentage === undefined ? '尚未估算' : `${format(percentage)}%`}><span style={{ width: `${Math.min(percentage ?? 0, 100)}%` }} /></div>
    <dl className="size-values">
      <div><dt>{current && result?.max_index ? `最大子请求 · 第 ${result.max_index} 份` : split ? '最大子请求规模' : '当前规模'}</dt><dd>{result?.cost === undefined ? '—' : format(result.cost)}</dd></div>
      <div><dt>单次上限</dt><dd>{result?.limit == null ? '—' : format(result.limit)}</dd></div>
    </dl>
    <button type="button" className="button" aria-label="刷新请求规模" disabled={!ready || disabled || costing.isPending} onClick={() => costing.mutate(snapshot)}>{costing.isPending ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}刷新估算</button>
    {data && !current && <p className="size-status" role="status">估算待刷新</p>}
    {current && exceeded && <p className="inline-error" role="status">{split ? `有 ${result?.over_limit_count} 份超过各自的单次上限。` : '超过单次请求上限。'}请缩小范围或增加拆分份数。</p>}
    {current && band && <p className={`size-priority ${band}`}>
      {band === 'high' ? '规模较高' : '规模偏高'}。过大的请求可能在 CDS 队列中被降低优先级。{' '}
      <a href={cdsRequestGuide} target="_blank" rel="noreferrer">CDS 官方建议</a>
    </p>}
    {current && result?.error && <p className="inline-error" role="alert">{result.error}</p>}
    <ErrorNotice error={costing.error} />
  </section>
}
