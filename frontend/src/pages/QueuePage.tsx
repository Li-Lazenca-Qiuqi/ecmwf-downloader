import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, RefreshCw, Search, X, Copy, FileText } from 'lucide-react'
import { api, type Task, type Summary } from '../lib/api'
import { ErrorNotice, Loading, StatusBadge, formatBytes, formatDate, statusLabels } from '../components'
import CardSelect from '../CardSelect'

const pageSize = 10
const statusOptions = [{ value: '', label: '全部状态' }, ...Object.entries(statusLabels).map(([value, label]) => ({ value, label }))]
const activeStates = ['queued', 'submitting', 'accepted', 'running', 'refreshing']
const directSources = new Map([
  ['mirror-ncar-era5', 'NCAR AWS'],
  ['mirror-ncar-gdex-era5', 'NCAR GDEX'],
])
function waitingReason(task: Task, summary?: Summary) {
  if (task.status === 'submission_unknown') return '需到官方请求页核实并关联远端 ID'
  if (task.error_message && task.next_retry_at) return '查询将重试：' + formatDate(task.next_retry_at)
  if (task.status === 'queued' && summary && !directSources.has(task.dataset_id) && !summary.available_accounts) return '等待可用 CDS 账号'
  if (task.status === 'cancelling') return '正在确认远端取消结果'
  return null
}
function useLinkCopy() {
  const [message, setMessage] = useState('')
  const copy = async (urls: string[]) => {
    try {
      await navigator.clipboard.writeText(urls.join('\n'))
      setMessage('已复制 ' + urls.length + ' 条链接')
    } catch {
      setMessage('无法访问剪贴板，请在详情中手动复制链接。')
    }
  }
  return { message, copy }
}
function retryLabel(task: Task) {
  if (task.status === 'failed' && task.remote_request_id && !['failed', 'rejected', 'dismissed'].includes(task.remote_status || ''))
    return task.cancel_requested ? '重试取消' : '继续监视'
  return '重新提交'
}
export default function QueuePage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('selected')
  const queryClient = useQueryClient()
  const links = useLinkCopy()
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary, refetchInterval: 5000 })
  const query = new URLSearchParams({ limit: String(pageSize), offset: String(offset) })
  if (search.trim()) query.set('search', search.trim())
  if (status) query.set('status', status)
  const tasks = useQuery({ queryKey: ['tasks', query.toString()], queryFn: () => api.tasks('?' + query), refetchInterval: 5000 })
  const action = useMutation({
    mutationFn: ({ id, operation }: { id: string; operation: 'cancel' | 'retry' | 'refresh' }) => api.action(id, operation),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
  })
  const refreshLinks = useMutation({
    mutationFn: async (ids: string[]) => {
      const results = await Promise.allSettled(ids.map(id => api.action(id, 'refresh')))
      const failures = results.filter(result => result.status === 'rejected').length
      if (failures) throw new Error(`${ids.length - failures} 个请求已开始更新，${failures} 个更新失败，请重试。`)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
  })
  const counts = summary.data?.by_status
  const total = tasks.data?.total ?? 0
  const items = tasks.data?.items ?? []
  const selectedItems = items.filter(task => selectedIds.has(task.id))
  const allSelected = items.length > 0 && selectedItems.length === items.length
  const readyItems = (selectedItems.length ? selectedItems : items).filter(task => task.status === 'completed')
  const readyUrls = readyItems.flatMap(task => task.results.map(asset => asset.url))
  const changePage = (nextOffset: number) => { setOffset(nextOffset); setSelectedIds(new Set()) }
  const toggleSelection = (id: string) => setSelectedIds(current => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })
  const actions = (task: Task) => <div className="row-actions">
    {(activeStates.includes(task.status) || (task.status === 'failed' && !!task.remote_request_id && !['failed','rejected','dismissed','expired'].includes(task.remote_status || ''))) && <button type="button" className="button danger" disabled={action.isPending} onClick={() => action.mutate({ id: task.id, operation: 'cancel' })}>取消</button>}
    {['failed', 'expired', 'cancelled'].includes(task.status) && <button type="button" className="button" disabled={action.isPending} onClick={() => action.mutate({ id: task.id, operation: 'retry' })}>{retryLabel(task)}</button>}
    {task.status === 'completed' && <>
      <button type="button" className="task-icon-button" title="复制链接" aria-label="复制链接"
        disabled={!task.results.length} onClick={() => void links.copy(task.results.map(asset => asset.url))}>
        <Copy size={17} aria-hidden="true" />
      </button>
      <button type="button" className="task-icon-button" title="查看详情" aria-label="查看详情" aria-haspopup="dialog"
        onClick={() => setParams({ selected: task.id })}>
        <FileText size={17} aria-hidden="true" />
      </button>
    </>}
    {task.status === 'submission_unknown' && <button type="button" className="button" onClick={() => setParams({ selected: task.id })}>核实提交</button>}
  </div>
  return <section className="page queue-page">
    <div className="page-heading"><div><h1>请求队列</h1><p>自动提交并监视远端处理，结果就绪后复制链接到下载器。</p></div><Link className="button primary" to="/requests/new"><Plus size={17} />提交请求</Link></div>
    <div className="queue-summary" aria-label="队列统计">
      <span>本地排队 <strong>{counts ? counts.queued ?? 0 : '—'}</strong></span>
      <span>远端排队 <strong>{counts ? counts.accepted ?? 0 : '—'}</strong></span>
      <span>处理中 <strong>{counts ? (counts.running ?? 0) + (counts.submitting ?? 0) + (counts.refreshing ?? 0) : '—'}</strong></span>
      <span>链接就绪 <strong>{counts ? counts.completed ?? 0 : '—'}</strong></span>
      <span>需处理 <strong>{counts ? (counts.failed ?? 0) + (counts.expired ?? 0) + (counts.submission_unknown ?? 0) : '—'}</strong></span>
      {summary.data?.max_workers != null && <span>后台 API 操作 <strong>{summary.data.active_workers} / {summary.data.max_workers}</strong></span>}
    </div>
    <ErrorNotice error={summary.error} />
    {summary.data && !summary.data.scheduler_running && <p className="notice">本服务未持有调度租约，请保持独立的 <code>ecmwf worker</code> 或另一个服务实例在后台监视。</p>}
    {summary.data && summary.data.available_accounts === 0 && <p className="notice">新的 CDS 请求等待可用账号，NCAR 文件链接不受影响。<Link to="/accounts">管理账号</Link></p>}
    <div className="panel">
      <div className="toolbar">
        <label className="search-field"><Search size={16} /><input aria-label="搜索请求" placeholder="搜索数据集、请求名称或远端 ID" value={search} onChange={event => { setSearch(event.target.value); changePage(0) }} /></label>
        <CardSelect label="请求状态" value={status} options={statusOptions}
          onChange={value => { setStatus(value); changePage(0) }} />
        {selectedItems.length > 0 && <span className="selection-count">已选 {selectedItems.length} 项</span>}
        <button type="button" className="button" disabled={!readyItems.length || refreshLinks.isPending} title={selectedItems.length ? '向源站重新查询已选请求的结果链接' : '向源站重新查询本页就绪请求的结果链接'} onClick={() => refreshLinks.mutate(readyItems.map(task => task.id))}><RefreshCw size={15} className={refreshLinks.isPending ? 'spin' : undefined} />更新链接</button>
        <button type="button" className="button" disabled={!readyUrls.length} title={selectedItems.length ? '将已选请求的就绪链接复制到剪贴板' : '将本页就绪请求的链接复制到剪贴板'} onClick={() => void links.copy(readyUrls)}><Copy size={15} />复制链接</button>
      </div>
      <ErrorNotice error={tasks.error || action.error || refreshLinks.error} />
      {tasks.isPending ? <Loading /> : <>
        <div className="table-scroll"><table className="task-table">
          <colgroup><col className="selection-column" /><col /><col className="status-column" /><col className="remote-column" /><col className="date-column" /><col className="actions-column" /></colgroup>
          <thead><tr>
            <th scope="col" className="selection-cell">
              <input type="checkbox" className="request-checkbox" aria-label="全选本页请求" title="全选本页请求"
                checked={allSelected} disabled={!items.length}
                ref={input => { if (input) input.indeterminate = selectedItems.length > 0 && !allSelected }}
                onChange={event => setSelectedIds(new Set(event.target.checked ? items.map(task => task.id) : []))} />
            </th>
            <th>数据请求</th><th>状态</th><th className="remote-cell">远端请求 ID</th><th className="date-cell">提交时间</th><th>操作</th>
          </tr></thead>
          <tbody>{items.map(task => <tr key={task.id} className={selectedIds.has(task.id) ? 'is-selected' : undefined}>
            <td className="selection-cell"><input type="checkbox" className="request-checkbox" aria-label={'选择请求 ' + task.title} checked={selectedIds.has(task.id)} onChange={() => toggleSelection(task.id)} /></td>
            <td>
              <button type="button" className="text-button filename" onClick={() => setParams({ selected: task.id })}>{task.title}</button>
              <small>{directSources.get(task.dataset_id) ?? 'CDS'} · {task.dataset_id}</small>
            </td>
            <td><StatusBadge status={task.status} /><small>{waitingReason(task, summary.data)}</small></td>
            <td className="remote-cell"><code>{task.remote_request_id || (directSources.has(task.dataset_id) ? '文件直链' : '—')}</code></td><td className="date-cell">{formatDate(task.created_at)}</td><td>{actions(task)}</td>
          </tr>)}</tbody></table></div>
        {!total && !tasks.isError && <p className="empty-state">{search || status ? '没有符合条件的请求。' : '暂无请求，提交后会自动监视并获取链接。'}</p>}
        <div className="table-footer"><div className="footer-summary"><span>共 {total} 个请求</span><span role="status">{links.message}</span></div><div className="pagination"><span>每页显示 {pageSize} 条</span><span>第 {items.length ? offset + 1 : 0}–{items.length ? offset + items.length : 0} 条</span><div className="row-actions"><button type="button" className="button" aria-label="上一页" disabled={!offset || tasks.isFetching} onClick={() => changePage(Math.max(0, offset - pageSize))}><ChevronLeft size={16} /></button><button type="button" className="button" aria-label="下一页" disabled={offset + pageSize >= total || tasks.isFetching} onClick={() => changePage(offset + pageSize)}><ChevronRight size={16} /></button></div></div></div>
      </>}
    </div>
    {selectedId && <TaskDetails key={selectedId} id={selectedId} onClose={() => setParams({})} />}
  </section>
}
function TaskDetails({ id, onClose }: { id: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const task = useQuery({ queryKey: ['tasks', 'detail', id], queryFn: () => api.task(id), refetchInterval: 5000 })
  const [remoteId, setRemoteId] = useState('')
  const client = useQueryClient()
  const links = useLinkCopy()
  const attach = useMutation({ mutationFn: () => api.attach(id, remoteId.trim()), onSuccess: () => void client.invalidateQueries({ queryKey: ['tasks'] }) })
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])
  const close = () => {
    dialog.current?.close()
    onClose()
  }
  return createPortal(<dialog ref={dialog} className="panel task-details" aria-labelledby="task-details-title"
    onCancel={event => { event.preventDefault(); close() }}
    onClick={event => { if (event.target === event.currentTarget) close() }}>
    <div className="task-details-content">
      <div className="section-heading">
        <h2 id="task-details-title">请求详情</h2>
        <button type="button" className="task-icon-button" onClick={close} title="关闭请求详情" aria-label="关闭请求详情">
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <ErrorNotice error={task.error || attach.error} />{task.isPending ? <Loading /> : task.data && <>
        <dl><dt>本地请求 ID</dt><dd>{task.data.id}</dd><dt>状态</dt><dd><StatusBadge status={task.data.status} /></dd><dt>远端请求 ID</dt><dd>{task.data.remote_request_id || '—'}</dd><dt>账号</dt><dd>{task.data.account_id || '无需账号或尚未分配'}</dd><dt>最近查询</dt><dd>{formatDate(task.data.checked_at)}</dd><dt>查询重试</dt><dd>{task.data.retry_count} / {task.data.max_retries}</dd></dl>
        {task.data.error_message && <p className="notice error">{task.data.error_message}</p>}
        {task.data.status === 'cancelling' && <p className="notice">取消尚待远端确认，确认前不会标记为已取消。</p>}
        {task.data.status === 'submission_unknown' && <div className="request-attach"><p className="helper">请先在官方请求页核实，再关联同一账号、数据集和参数的远端 ID；不会自动重复提交。</p><label>远端请求 ID<input aria-label="关联远端请求 ID" value={remoteId} onChange={event => setRemoteId(event.target.value)} /></label><button type="button" className="button" disabled={!remoteId.trim() || attach.isPending} onClick={() => attach.mutate()}>关联并继续</button></div>}
        {task.data.status === 'completed' && <div className="request-results" aria-label="结果链接">
          <h3>结果链接</h3><p className="helper">复制到专业下载器使用；源站缓存清理后链接可能失效。</p>
          {task.data.results.map((asset, index) => <section className="result-asset" key={asset.url}><strong>{asset.filename || '结果 ' + (index + 1)}</strong><input aria-label={'下载链接 ' + (index + 1)} value={asset.url} readOnly onFocus={event => event.target.select()} /><div className="result-meta"><span>{asset.size === null ? '大小未提供' : formatBytes(asset.size)}</span><span>{asset.content_type || '类型未提供'}</span><span>{asset.expires_at ? '有效期至 ' + formatDate(asset.expires_at) : '有效期未提供'}</span></div><button type="button" className="button" onClick={() => void links.copy([asset.url])}><Copy size={14} />复制此链接</button></section>)}
          {links.message && <p className="helper" role="status">{links.message}</p>}
        </div>}
        {task.data.status === 'expired' && <p className="notice">远端结果已不可用；可通过“重新提交”明确发起新请求。</p>}
        <details><summary>请求参数</summary><pre>{JSON.stringify(task.data.request_payload, null, 2)}</pre></details>
      </>}
    </div>
  </dialog>, document.body)
}
