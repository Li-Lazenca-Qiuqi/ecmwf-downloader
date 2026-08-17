import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, AlertTriangle, Check, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight,
  CircleHelp, Cloud, Database, Download, Eye, Folder, Gauge, Grid2X2, List, Loader2,
  Menu, MoreVertical, PauseCircle, Play, Plus, RefreshCw, Search, Server, Settings,
  SlidersHorizontal, Trash2, Users, X, Zap,
} from 'lucide-react'
import { api, type Account, type Task, type TaskStatus } from './lib/api'
import brandMark from './assets/brand-mark.png'

const navItems = [
  { to: '/', label: '概览', icon: Grid2X2 },
  { to: '/requests/new', label: '创建请求', icon: Plus },
  { to: '/tasks', label: '任务队列', icon: List },
  { to: '/activity', label: '下载活动', icon: Download },
  { to: '/accounts', label: '账号池', icon: Users },
  { to: '/settings', label: '设置', icon: Settings },
]

function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const queryClient = useQueryClient()
  const title = navItems.find((item) => item.to === location.pathname)?.label || (location.pathname === '/requests/new' ? '创建请求' : 'ECMWF Downloader')
  useEffect(() => {
    const source = new EventSource('/api/v1/events')
    const refresh = () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    }
    const eventTypes = ['task.created', 'task.status_changed', 'task.progress', 'task.retry_scheduled', 'task.recovered', 'task.deleted']
    eventTypes.forEach((eventType) => source.addEventListener(eventType, refresh))
    source.onerror = () => {
      // EventSource reconnects automatically; polling queries remain the fallback.
    }
    return () => {
      eventTypes.forEach((eventType) => source.removeEventListener(eventType, refresh))
      source.close()
    }
  }, [queryClient])
  return <div className={`app-shell ${collapsed ? 'nav-collapsed' : ''}`}>
    <aside className="sidebar">
      <Link to="/" className="brand">
        <img src={brandMark} alt="" />
        {!collapsed && <span><strong>ECMWF</strong><strong>Downloader</strong></span>}
      </Link>
      <nav className="primary-nav">
        {navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title={label}>
          <Icon size={19} strokeWidth={1.8} /><span>{!collapsed && label}</span>
        </NavLink>)}
      </nav>
      <button className="collapse-button" onClick={() => setCollapsed((value) => !value)}><ChevronLeft size={16} className={collapsed ? 'rotate-180' : ''} />{!collapsed && '收起导航'}</button>
    </aside>
    <main className="main-shell">
      <header className="topbar">
        <div className="topbar-title"><button className="mobile-menu" onClick={() => setCollapsed((value) => !value)}><Menu size={20} /></button><h1>{title === '概览' ? 'ECMWF Downloader' : title}</h1><span className="workspace"><Folder size={16} />本地工作区<ChevronDown size={14} /></span></div>
        <div className="topbar-actions"><span className="service-status"><span className="status-dot" />服务运行中</span><Link className="button primary" to="/requests/new"><Plus size={17} />新建下载任务</Link><button className="avatar">◎</button></div>
      </header>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/requests/new" element={<RequestBuilderPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/activity" element={<ActivityPage />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
      <footer className="statusbar"><span><Database size={16} />数据库：SQLite <i className="status-dot" />健康</span><span><Folder size={16} />输出目录：本地配置 <i className="status-dot" />可用</span><span><RefreshCw size={14} />最后检查：刚刚</span></footer>
    </main>
  </div>
}

function StatStrip() {
  const { data } = useQuery({ queryKey: ['summary'], queryFn: api.summary, refetchInterval: 5000 })
  const counts = (data?.by_status || {}) as Record<string, number>
  const stats = [
    ['待处理', counts.pending || 0, 'blue', Gauge], ['下载中', counts.running || 0, 'blue', Download], ['已完成', counts.completed || 0, 'green', CheckCircle2], ['失败', counts.failed || 0, 'red', AlertTriangle], ['并发', `${data?.active_workers || 0} / 4`, 'violet', Activity],
  ] as const
  return <div className="stat-strip">{stats.map(([label, value, tone, Icon]) => <div className="stat" key={label}><Icon className={`tone-${tone}`} size={27} strokeWidth={1.7} /><div><span>{label}</span><strong>{value}</strong></div></div>)}</div>
}

function Overview() {
  return <div className="page overview-page"><StatStrip /><div className="overview-grid"><section className="table-section"><div className="section-heading"><h2>最近任务</h2><TaskToolbar /></div><TaskTable compact /></section><ActivityRail /></div></div>
}

function TaskToolbar() {
  const queryClient = useQueryClient()
  return <div className="toolbar"><label className="search-field"><Search size={16} /><input placeholder="搜索任务、数据集或文件名..." onChange={(event) => queryClient.setQueryData(['task-search'], event.target.value)} /></label><button className="select-button">状态：全部 <ChevronDown size={14} /></button><button className="icon-button" onClick={() => queryClient.invalidateQueries({ queryKey: ['tasks'] })}><RefreshCw size={16} />刷新</button></div>
}

function statusLabel(status: TaskStatus) {
  return ({ pending: '待处理', queued: '排队中', running: '下载中', completed: '已完成', failed: '失败', retry_wait: '重试中', cancelling: '取消中', cancelled: '已取消' } as Record<string, string>)[status] || status
}

function StatusBadge({ status }: { status: TaskStatus }) {
  const icon = status === 'completed' ? <Check size={13} /> : status === 'failed' ? <AlertTriangle size={13} /> : status === 'running' ? <Download size={13} /> : status === 'retry_wait' ? <RefreshCw size={13} /> : <PauseCircle size={13} />
  return <span className={`status-badge ${status}`} >{icon}{statusLabel(status)}</span>
}

function TaskTable({ compact = false }: { compact?: boolean }) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['tasks'], queryFn: () => api.tasks(`?limit=${compact ? 10 : 50}`), refetchInterval: 5000 })
  const action = useMutation({ mutationFn: ({ id, value }: { id: string; value: 'enqueue' | 'cancel' | 'retry' }) => api.action(id, value), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }) })
  if (isLoading) return <div className="loading"><Loader2 className="spin" />加载任务...</div>
  const tasks = data?.items || []
  return <div className="table-wrap"><table className="data-table"><thead><tr><th className="check-col"><input type="checkbox" /></th><th>任务</th><th>数据集</th><th>输出文件</th><th>状态</th><th>进度</th><th>账号</th><th>创建时间</th><th>操作</th></tr></thead><tbody>{tasks.map((task) => <tr key={task.id}><td><input type="checkbox" /></td><td><Link className="task-link" to={`/tasks?selected=${task.id}`}>{task.id.slice(0, 13)}</Link></td><td className="dataset-cell">{task.dataset_id}</td><td>{task.filename}</td><td><StatusBadge status={task.status} /></td><td><ProgressValue task={task} /></td><td>{task.account_id || '—'}</td><td>{new Date(task.created_at).toLocaleString('zh-CN', { hour12: false })}</td><td><div className="row-actions"><button className="icon-button" title="查看"><Eye size={15} /></button>{task.status === 'pending' && <button className="icon-button" title="入队" onClick={() => action.mutate({ id: task.id, value: 'enqueue' })}><Play size={15} /></button>}{['running', 'queued', 'retry_wait'].includes(task.status) && <button className="icon-button danger" title="取消" onClick={() => action.mutate({ id: task.id, value: 'cancel' })}><X size={15} /></button>}<button className="icon-button" title="更多"><MoreVertical size={15} /></button></div></td></tr>)}</tbody></table>{!tasks.length && <EmptyState title="暂无任务" detail="创建一个通用 CDS 请求后，任务会出现在这里。" />}<div className="table-footer"><span>共 {data?.total || 0} 条</span>{!compact && <span className="pagination"><button className="icon-button"><ChevronLeft size={15} /></button><button className="page-current">1</button><button className="icon-button"><ChevronRight size={15} /></button></span>}</div></div>
}

function ProgressValue({ task }: { task: Task }) {
  const value = task.progress
  return <div className="progress-cell"><span>{value == null ? '—' : `${Math.round(value)}%`}</span>{value != null && <div className="progress-track"><i style={{ width: `${value}%` }} /></div>}</div>
}

function ActivityRail() {
  const { data } = useQuery({ queryKey: ['tasks', 'active'], queryFn: () => api.tasks('?status=running&limit=8'), refetchInterval: 3000 })
  const active = data?.items || []
  return <section className="activity-rail"><div className="section-heading"><h2>下载活动</h2><div className="toolbar"><button className="icon-button"><Play size={15} />全部入队</button><button className="icon-button danger"><PauseCircle size={15} />停止调度</button></div></div><div className="worker-table"><div className="worker-header"><span>工作器 / 账号</span><span>文件名</span><span>状态 / 进度</span><span>重试倒计时</span></div>{active.map((task) => <div className="worker-row" key={task.id}><div><strong>Worker</strong><small><i className="status-dot" />{task.account_id || '等待分配'}</small></div><span>{task.filename}</span><div><StatusBadge status={task.status} /><ProgressValue task={task} /></div><span>—</span></div>)}{!active.length && <div className="empty-rail"><Activity size={22} /><span>当前没有活动下载</span></div>}<div className="worker-footer">并发使用：{active.length} / 4 <Link to="/activity">查看全部活动 <ChevronRight size={14} /></Link></div></div></section>
}

function EmptyState({ title, detail }: { title: string; detail: string }) { return <div className="empty-state"><Cloud size={28} /><strong>{title}</strong><span>{detail}</span></div> }

function TasksPage() { return <div className="page"><div className="section-heading page-heading"><div><h2>任务队列</h2><p>筛选、入队和控制所有下载任务。</p></div><Link className="button primary" to="/requests/new"><Plus size={16} />创建任务</Link></div><div className="full-table-panel"><div className="toolbar"><TaskToolbar /></div><TaskTable /></div></div> }

function ActivityPage() { return <div className="page"><div className="section-heading page-heading"><div><h2>下载活动</h2><p>实时查看 Worker、账号与取消请求状态。</p></div><span className="service-status"><span className="status-dot" />调度器运行中</span></div><div className="activity-page-grid"><ActivityRail /><div className="event-panel"><h3>事件流</h3><p>来自 CLI、Web 和 Worker 的任务事件会通过 SSE 同步。</p><div className="event-line"><span className="status-dot" />等待新事件</div></div></div></div> }

function RequestBuilderPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [datasetId, setDatasetId] = useState('reanalysis-era5-pressure-levels')
  const [split, setSplit] = useState('none')
  const [prompt, setPrompt] = useState('')
  const [payload, setPayload] = useState<Record<string, unknown>>({ variable: ['temperature'], year: [2024], month: ['01', '02', '03'], time: ['00:00', '06:00', '12:00', '18:00'], data_format: 'netcdf', download_format: 'unarchived' })
  const { data: datasets } = useQuery({ queryKey: ['datasets'], queryFn: api.datasets })
  const { data: schema } = useQuery({ queryKey: ['schema', datasetId], queryFn: () => api.schema(datasetId) })
  const preview = useMutation({ mutationFn: () => api.preview({ dataset_id: datasetId, request_payload: payload, split_strategy: split }), })
  const create = useMutation({ mutationFn: () => api.createTasks({ dataset_id: datasetId, request_payload: payload, split_strategy: split, enqueue: true }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tasks'] }); navigate('/tasks') } })
  const suggestion = useMutation({
    mutationFn: () => api.suggestion({ field_schema: { fields: schema?.fields || [] }, user_request: prompt }),
    onSuccess: ({ suggestion: value }) => {
      if (value && typeof value === 'object') {
        const next = (value as any).parameters || (value as any).request_payload || value
        if (next && typeof next === 'object') setPayload((old) => ({ ...old, ...next }))
      }
    },
  })
  const fields = (schema?.fields || []).slice(0, 12)
  const setField = (name: string, value: string) => setPayload((old) => ({ ...old, [name]: value.includes(',') ? value.split(',').map((item) => item.trim()) : value }))
  return <div className="page request-page"><div className="stepper"><span className="done"><Check size={15} />1 数据集</span><i /><span className="active">2 参数</span><i /><span>3 输出与拆分</span><i /><span>4 确认</span></div><div className="request-grid"><section className="request-form"><div className="dataset-row"><label>数据集<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{(datasets?.items || [{ id: datasetId, title: datasetId }]).map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}</select></label><button className="button secondary" onClick={() => queryClient.invalidateQueries({ queryKey: ['schema', datasetId] })}><RefreshCw size={15} />刷新 Schema</button></div><p className="helper">来源：ECMWF CDS　·　动态 Schema 字段　·　提交前可预览原始请求</p><div className="section-heading form-heading"><h3>请求参数</h3><button className="button secondary" disabled={suggestion.isPending || !prompt} onClick={() => suggestion.mutate()}><Zap size={15} />{suggestion.isPending ? '生成中…' : 'AI 填写参数'}</button></div><div className="ai-helper"><span>用自然语言描述你的需求，AI 只生成可审核的参数建议。</span><div><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="下载 2024 年 1–3 月东亚区域 500/700/850 hPa 的温度与位势高度" /><button className="button secondary" disabled={suggestion.isPending || !prompt} onClick={() => suggestion.mutate()}>生成建议 <Zap size={14} /></button></div>{suggestion.error && <div className="error-box"><AlertTriangle size={15} />{suggestion.error.message}</div>}</div><div className="field-list">{fields.length ? fields.map((field: any) => <label className="schema-field" key={field.name}><span>{field.name}<CircleHelp size={13} /></span><input value={Array.isArray(payload[field.name]) ? (payload[field.name] as unknown[]).join(',') : String(payload[field.name] ?? '')} onChange={(event) => setField(field.name, event.target.value)} placeholder={field.values?.length ? field.values.slice(0, 3).join(', ') : '输入值，逗号分隔'} /></label>) : <><label className="schema-field"><span>variable</span><input value="temperature" onChange={() => undefined} /></label><label className="schema-field"><span>year</span><input value="2024" onChange={() => undefined} /></label></>}</div><h3 className="subsection-title">输出与拆分</h3><div className="output-grid"><label>输出目录<input value="data/downloads" readOnly /></label><label>拆分策略<select value={split} onChange={(event) => setSplit(event.target.value)}><option value="none">不拆分</option><option value="year">按年</option><option value="month">按月</option></select></label><label>最大重试<input type="number" value="3" readOnly /></label></div><div className="action-bar"><button className="button secondary">重置</button><div><button className="button secondary">保存为模板</button><button className="button secondary" onClick={() => preview.mutate()}>仅创建任务</button><button className="button primary" onClick={() => create.mutate()}>{create.isPending ? <Loader2 className="spin" size={15} /> : <Download size={15} />}创建并入队</button></div></div></section><aside className="preview-panel"><div className="preview-heading"><h3>请求预览</h3><button className="icon-button" onClick={() => preview.mutate()}><RefreshCw size={15} />刷新</button></div><div className="preview-tabs"><button className="selected">结构化</button><button>JSON</button></div><div className="preview-content"><h4>数据集信息</h4><dl><dt>数据集</dt><dd>{datasetId}</dd><dt>来源</dt><dd>ECMWF CDS</dd><dt>参数项</dt><dd>{Object.keys(payload).length} 项</dd></dl><h4>请求参数</h4><pre>{JSON.stringify(payload, null, 2)}</pre>{preview.data && <><h4>任务预览（将创建 {preview.data.items.length} 个任务）</h4><div className="preview-ok"><CheckCircle2 size={17} />参数校验通过</div></>}{preview.error && <div className="error-box"><AlertTriangle size={16} />{preview.error.message}</div>}</div></aside></div></div>
}

function AccountsPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState<Account | null>(null)
  const { data, isLoading } = useQuery({ queryKey: ['accounts'], queryFn: api.accounts })
  const test = useMutation({ mutationFn: (id: string) => api.testAccount(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }) })
  const accounts = data?.items || []
  return <div className="page accounts-page"><div className="section-heading page-heading"><div><h2>账号池 <small>{accounts.length} 个账号 · {accounts.filter((item) => item.status === 'active').length} 个可用</small></h2></div><div><button className="button secondary" onClick={() => accounts.forEach((item) => test.mutate(item.id))}><RefreshCw size={15} />测试全部连接</button><button className="button primary" onClick={() => setOpen({ id: '', email: '', url: 'https://cds.climate.copernicus.eu/api', status: 'active', used_count: 0, fail_count: 0, last_used: null, last_error: null })}><Plus size={16} />添加账号</button></div></div><div className="account-layout"><section className="account-table-panel"><div className="toolbar"><label className="search-field"><Search size={16} /><input placeholder="搜索账号（邮箱）..." /></label><button className="select-button">状态：全部 <ChevronDown size={14} /></button></div>{isLoading ? <div className="loading"><Loader2 className="spin" />加载账号...</div> : <table className="data-table account-table"><thead><tr><th><input type="checkbox" /></th><th>账号</th><th>API 地址</th><th>状态</th><th>已使用</th><th>连续失败</th><th>最后使用</th><th>操作</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.id} className={open?.id === account.id ? 'selected-row' : ''}><td><input type="checkbox" checked={open?.id === account.id} onChange={() => setOpen(account)} /></td><td><strong>{account.email}</strong></td><td className="muted-cell">{account.url}</td><td><span className={`account-status ${account.status}`}><i />{account.status === 'active' ? '可用' : account.status === 'disabled' ? '已禁用' : '连接异常'}</span></td><td>{account.used_count}</td><td>{account.fail_count}</td><td>{account.last_used ? new Date(account.last_used).toLocaleString('zh-CN') : '—'}</td><td><button className="text-action" onClick={() => test.mutate(account.id)}>测试</button><button className="text-action" onClick={() => setOpen(account)}>编辑</button><button className="icon-button"><MoreVertical size={15} /></button></td></tr>)}</tbody></table>}{!accounts.length && <EmptyState title="暂无账号" detail="添加 CDS API 账号后才能启动下载。" />}<div className="rule-strip"><CircleHelp size={16} />连续失败 5 次后自动禁用 <button className="text-action">编辑规则</button><span>可用账号　{accounts.filter((item) => item.status === 'active').length} / {accounts.length}</span></div></section>{open && <AccountDrawer account={open} onClose={() => setOpen(null)} onSaved={() => { setOpen(null); queryClient.invalidateQueries({ queryKey: ['accounts'] }) }} />}</div></div>
}

function AccountDrawer({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void }) {
  const [email, setEmail] = useState(account.email)
  const [key, setKey] = useState('')
  const [url, setUrl] = useState(account.url)
  const [status, setStatus] = useState<Account['status']>(account.status)
  const save = useMutation({
    mutationFn: async () => {
      const updated = account.id
        ? await api.updateAccount(account.id, { email, ...(key ? { key } : {}), url })
        : await api.addAccount({ email, key, url })
      if (account.id && status !== account.status && status !== 'error') {
        await api.accountAction(account.id, status === 'active' ? 'enable' : 'disable')
      }
      return updated
    },
    onSuccess: onSaved,
  })
  const test = useMutation({ mutationFn: () => api.testAccount(account.id), onSuccess: onSaved })
  const remove = useMutation({ mutationFn: () => api.deleteAccount(account.id), onSuccess: onSaved })
  return <aside className="drawer"><div className="drawer-heading"><h2>{account.id ? '编辑 CDS 账号' : '添加 CDS 账号'}</h2><button className="icon-button" onClick={onClose}><X size={18} /></button></div><div className="drawer-content"><label>显示邮箱<input value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>API Key<input type="password" value={key} onChange={(event) => setKey(event.target.value)} placeholder={account.id ? '保持不变' : '输入 CDS API Key'} /></label><p className="helper">API Key 仅存储在本地工作区，不会上传或同步。</p><label>API 地址<input value={url} onChange={(event) => setUrl(event.target.value)} /></label><label>状态<select value={status} onChange={(event) => setStatus(event.target.value as Account['status'])}><option value="active">可用</option><option value="disabled">已禁用</option></select></label><h4>使用数据（只读）</h4><div className="usage-strip"><span><small>使用次数</small><strong>{account.used_count}</strong></span><span><small>连续失败</small><strong>{account.fail_count}</strong></span><span><small>最后成功</small><strong>{account.last_used ? new Date(account.last_used).toLocaleString('zh-CN') : '—'}</strong></span></div>{account.last_error && <div className="error-box"><AlertTriangle size={16} />{account.last_error}</div>}</div><div className="drawer-actions"><button className="button secondary" onClick={onClose}>取消</button>{account.id && <button className="button secondary" disabled={test.isPending} onClick={() => test.mutate()}>{test.isPending ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}测试连接</button>}<button className="button primary" disabled={save.isPending || !email || (!key && !account.id)} onClick={() => save.mutate()}>{save.isPending ? <Loader2 className="spin" size={15} /> : <Check size={15} />}保存修改</button></div>{account.id && <button className="delete-account" disabled={remove.isPending} onClick={() => window.confirm('确认删除这个账号？') && remove.mutate()}><Trash2 size={16} />删除账号</button>}</aside>
}

function SettingsPage() { const { data } = useQuery({ queryKey: ['settings'], queryFn: api.settings }); return <div className="page"><div className="section-heading page-heading"><div><h2>设置</h2><p>本机数据库、下载目录和并发行为。</p></div></div><section className="settings-panel"><div className="settings-row"><div><h3>下载目录</h3><p>任务输出文件和临时 .part 文件保存位置。</p></div><code>{String((data?.download as any)?.output_dir || 'data/downloads')}</code></div><div className="settings-row"><div><h3>最大并发</h3><p>调度器同时运行的 CDS 请求数量。</p></div><strong>{String((data?.download as any)?.max_workers || 4)}</strong></div><div className="settings-row"><div><h3>重试策略</h3><p>失败后使用退避等待，达到上限后标记失败。</p></div><code>{JSON.stringify((data?.download as any)?.retry_delays || [5, 15, 60])}</code></div><div className="settings-row"><div><h3>AI 参数助手</h3><p>仅在启用并配置兼容 OpenAI API 后可用。</p></div><span className="account-status disabled"><i />未配置</span></div></section></div> }

export default function App() { return <AppShell /> }
