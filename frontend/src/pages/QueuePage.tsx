import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, RefreshCw, Search, X } from 'lucide-react'
import { api, type Summary, type Task } from '../lib/api'
import { ErrorNotice, Loading, StatusBadge, formatBytes, formatDate, statusLabels } from '../components'

const pageSize = 20
function waitingReason(task: Task, summary?: Summary) {
  if (task.status === 'pending') return '保留的历史任务，尚未启动'
  if (task.status === 'retry_wait') return task.next_retry_at ? `下次重试：${formatDate(task.next_retry_at)}` : '等待自动重试'
  if (task.status === 'cancelling') return '正在等待当前请求结束'
  if (task.status !== 'queued' || !summary) return null
  if (!summary.available_accounts) return '等待可用账号'
  if (!summary.scheduler_running) return '等待后台 Worker 消费'
  if (summary.max_workers && summary.active_workers >= summary.max_workers) return '等待下载空位'
  return '等待调度'
}
function Progress({ task }: { task: Task }) {
  return <div className="task-progress">
    {task.progress === null ? <span>{task.downloaded_bytes ? formatBytes(task.downloaded_bytes) : '—'}</span> : <><progress value={task.progress} max={100} aria-label="下载进度" /><span>{Math.round(task.progress)}%</span></>}
  </div>
}
export default function QueuePage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const [params, setParams] = useSearchParams()
  const selected = params.get('selected')
  const queryClient = useQueryClient()
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary, refetchInterval: 5000 })
  const query = new URLSearchParams({ limit: String(pageSize), offset: String(offset) })
  if (search.trim()) query.set('search', search.trim())
  if (status) query.set('status', status)
  const tasks = useQuery({ queryKey: ['tasks', query.toString()], queryFn: () => api.tasks(`?${query}`), refetchInterval: 5000 })
  const action = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'cancel' | 'retry' }) => api.action(id, action),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
  })
  const counts = summary.data?.by_status
  const total = tasks.data?.total ?? 0
  const closeDetails = () => setParams({})
  const actions = (task: Task) => <div className="row-actions">
    {['pending', 'queued', 'running', 'retry_wait'].includes(task.status) && <button className="button danger" disabled={action.isPending} onClick={() => action.mutate({ id: task.id, action: 'cancel' })}>取消</button>}
    {task.status === 'failed' && <button className="button" disabled={action.isPending} onClick={() => action.mutate({ id: task.id, action: 'retry' })}>重试</button>}
  </div>
  return <section className="page">
    <div className="page-heading"><div><h1>任务队列</h1><p>添加后自动下载，排队中的任务会在有空位时开始。</p></div><Link className="button primary" to="/requests/new"><Plus size={17} />添加任务</Link></div>
    <div className="queue-summary" aria-label="队列统计">
      <span>排队 <strong>{counts ? counts.queued ?? 0 : '—'}</strong></span>
      <span>下载 <strong>{counts ? counts.running ?? 0 : '—'}</strong></span>
      <span>重试等待 <strong>{counts ? counts.retry_wait ?? 0 : '—'}</strong></span>
      <span>完成 <strong>{counts ? counts.completed ?? 0 : '—'}</strong></span>
      <span>失败 <strong>{counts ? counts.failed ?? 0 : '—'}</strong></span>
      {summary.data?.max_workers != null && <span>并发 <strong>{summary.data.active_workers} / {summary.data.max_workers}</strong></span>}
    </div>
    <ErrorNotice error={summary.error} />
    {summary.data && !summary.data.scheduler_running && <p className="notice">本服务未运行调度器。请保持独立的 <code>ecmwf worker</code> 在后台运行，任务会由它自动消费。</p>}
    {summary.data && summary.data.available_accounts === 0 && <p className="notice">没有可用账号，任务将保留在队列中。<Link to="/accounts">添加或启用 CDS 账号</Link></p>}
    <div className="panel">
      <div className="toolbar">
        <label className="search-field"><Search size={16} /><input aria-label="搜索任务" placeholder="搜索任务、数据集或文件名" value={search} onChange={(event) => { setSearch(event.target.value); setOffset(0) }} /></label>
        <select aria-label="任务状态" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0) }}><option value="">全部状态</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
        <button className="button" onClick={() => { void tasks.refetch(); void summary.refetch() }}><RefreshCw size={15} />刷新</button>
      </div>
      <ErrorNotice error={tasks.error || action.error} />
      {tasks.isPending ? <Loading /> : <>
        <div className="table-scroll"><table className="task-table"><thead><tr><th>下载任务</th><th>状态</th><th>进度</th><th>添加时间</th><th>操作</th></tr></thead>
          <tbody>{tasks.data?.items.map((task) => <tr key={task.id}>
            <td><button className="text-button filename" onClick={() => setParams({ selected: task.id })}>{task.filename}</button><small>{task.dataset_id}</small></td>
            <td><StatusBadge status={task.status} /><small>{waitingReason(task, summary.data)}</small></td>
            <td><Progress task={task} /></td><td className="date-cell">{formatDate(task.created_at)}</td><td>{actions(task)}</td>
          </tr>)}</tbody></table></div>
        {!total && !tasks.isError && <p className="empty-state">{search || status ? '没有符合条件的任务。' : '暂无任务，添加一个下载请求即可开始。'}</p>}
        <div className="table-footer"><span>共 {total} 个任务{total > 0 ? ` · 当前 ${offset + 1}–${Math.min(offset + pageSize, total)}` : ''}</span><div className="row-actions"><button className="button" aria-label="上一页" disabled={!offset || tasks.isFetching} onClick={() => setOffset(Math.max(0, offset - pageSize))}><ChevronLeft size={16} /></button><button className="button" aria-label="下一页" disabled={offset + pageSize >= total || tasks.isFetching} onClick={() => setOffset(offset + pageSize)}><ChevronRight size={16} /></button></div></div>
      </>}
    </div>
    {selected && <TaskDetails id={selected} onClose={closeDetails} />}
  </section>
}
function TaskDetails({ id, onClose }: { id: string; onClose: () => void }) {
  const task = useQuery({ queryKey: ['tasks', 'detail', id], queryFn: () => api.task(id), refetchInterval: 5000 })
  return <section className="panel task-details" aria-label="任务详情"><div className="section-heading"><h2>任务详情</h2><button className="button" onClick={onClose} aria-label="关闭任务详情"><X size={16} /></button></div>
    <ErrorNotice error={task.error} />{task.isPending ? <Loading /> : task.data && <>
      <dl><dt>任务 ID</dt><dd>{task.data.id}</dd><dt>状态</dt><dd><StatusBadge status={task.data.status} /></dd><dt>输出路径</dt><dd>{task.data.output_path}</dd><dt>账号</dt><dd>{task.data.account_id || '尚未分配'}</dd><dt>已下载</dt><dd>{formatBytes(task.data.downloaded_bytes)}</dd><dt>失败重试</dt><dd>{task.data.retry_count} / {task.data.max_retries}</dd></dl>
      {task.data.status === 'cancelling' && <p className="notice">取消请求已接受。当前 CDS 请求可能需要一段时间才能结束，任务不会自动重试。</p>}
      {task.data.error_message && <p className="notice error">{task.data.error_message}</p>}
      <details><summary>请求参数</summary><pre>{JSON.stringify(task.data.request_payload, null, 2)}</pre></details>
    </>}
  </section>
}
