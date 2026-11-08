import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Radio, X } from 'lucide-react'
import { api, type Account } from '../lib/api'
import { ErrorNotice, Loading, formatDate } from '../components'
import CardSelect from '../CardSelect'

const accountLabels = { active: '可用', busy: '繁忙', disabled: '已禁用', error: '连接异常' }
const emptyAccount: Account = { id: '', email: '', url: 'https://cds.climate.copernicus.eu/api', status: 'active', is_busy: false, used_count: 0, today_used_count: 0, fail_count: 0, last_used: null, last_error: null }
type ConnectionResult = Awaited<ReturnType<typeof api.testAccount>>

export default function AccountsPage() {
  const [open, setOpen] = useState<Account | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [testResults, setTestResults] = useState<Map<string, ConnectionResult | null>>(new Map())
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.accounts, refetchInterval: 10000 })
  const test = useMutation({
    mutationFn: async (ids: string[]) => {
      for (const id of ids) {
        const result = await api.testAccount(id).catch((error: unknown) => ({
          ok: false,
          message: error instanceof Error ? error.message : '连接测试失败，请重试。',
        }))
        setTestResults(current => new Map(current).set(id, result))
      }
    },
  })
  const items = accounts.data?.items ?? []
  const selected = items.filter(account => selectedIds.has(account.id))
  const allSelected = items.length > 0 && selected.length === items.length
  const pendingIds = test.isPending ? test.variables.filter(id => testResults.get(id) === null) : []

  const toggle = (id: string) => setSelectedIds(current => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })

  const startTests = (ids: string[]) => {
    setTestResults(current => {
      const next = new Map(current)
      for (const id of ids) next.set(id, null)
      return next
    })
    test.mutate(ids)
  }

  const saved = (deleted = false) => {
    const id = open?.id
    if (id) {
      setTestResults(current => {
        const next = new Map(current)
        next.delete(id)
        return next
      })
      if (deleted) setSelectedIds(current => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
    }
    setOpen(null)
    void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    void queryClient.invalidateQueries({ queryKey: ['summary'] })
  }

  return <section className="page">
    <div className="page-heading"><div><h1>CDS 账号</h1><p>提交 CDS 请求时自动选择可用账号，后续用同一账号查询结果。</p></div><button className="button primary" onClick={() => setOpen(emptyAccount)}><Plus size={17} />添加账号</button></div>
    <ErrorNotice error={accounts.error} />
    {accounts.isPending ? <Loading /> : <div className="panel">
      <div className="toolbar">
        <button type="button" className="button" disabled={!selected.length || test.isPending}
          onClick={() => startTests(selected.map(account => account.id))}><Radio size={16} />批量测试连接</button>
        {selected.length > 0 && <span className="selection-count">已选 {selected.length} 个账号</span>}
      </div>
      <div className="table-scroll"><table className="account-table" aria-label="CDS 账号列表">
        <thead><tr>
          <th scope="col" className="selection-cell">
            <input type="checkbox" className="request-checkbox" aria-label="全选账号" checked={allSelected}
              disabled={!items.length}
              ref={input => { if (input) input.indeterminate = selected.length > 0 && !allSelected }}
              onChange={event => setSelectedIds(new Set(event.target.checked ? items.map(account => account.id) : []))} />
          </th>
          <th scope="col">账号</th><th scope="col">状态</th><th scope="col">今日使用次数</th><th scope="col">连续失败</th><th scope="col">最后使用</th><th scope="col">操作</th>
        </tr></thead>
        <tbody>{items.map(account => {
          const result = testResults.get(account.id)
          const checking = pendingIds[0] === account.id
          const pending = pendingIds.includes(account.id)
          const status = account.status === 'active' && (account.is_busy || checking) ? 'busy' : account.status
          return <tr key={account.id} className={selectedIds.has(account.id) ? 'is-selected' : undefined}>
            <td className="selection-cell">
              <input type="checkbox" className="request-checkbox" aria-label={'选择账号 ' + account.email}
                checked={selectedIds.has(account.id)} onChange={() => toggle(account.id)} />
            </td>
            <td className="account-email">{account.email}</td>
            <td>
              <span className={`account-status ${status}`}>{accountLabels[status]}</span>
              {pending && <small className="account-test-result" role="status">{checking ? '正在测试连接…' : '等待测试…'}</small>}
              {result && <small className={`account-test-result ${result.ok ? 'passed' : 'failed'}`}
                role={result.ok ? 'status' : 'alert'} title={result.ok ? result.message : undefined}>
                {result.ok ? '认证通过' : result.message}
              </small>}
            </td>
            <td title="按后台本地时间统计今天首次取得结果链接的请求">{account.today_used_count ?? '—'}</td>
            <td>{account.fail_count}</td><td className="date-cell">{formatDate(account.last_used)}</td>
            <td><div className="row-actions">
              <button type="button" className="button" disabled={test.isPending}
                onClick={() => startTests([account.id])}>{checking ? '测试中…' : '测试连接'}</button>
              <button type="button" className="button" disabled={pending} onClick={() => setOpen(account)}>编辑</button>
            </div></td>
          </tr>
        })}{items.length === 0 && <tr><td colSpan={7} className="empty-state">暂无账号。添加 CDS API 账号后可提交 CDS 请求。</td></tr>}</tbody>
      </table></div>
    </div>}
    {open && <div className="dialog-backdrop"><AccountEditor key={open.id || 'new'} account={open} onClose={() => setOpen(null)} onSaved={saved} /></div>}
  </section>
}
function AccountEditor({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: (deleted?: boolean) => void }) {
  const [email, setEmail] = useState(account.email)
  const [key, setKey] = useState('')
  const [url, setUrl] = useState(account.url)
  const [status, setStatus] = useState(account.status)
  const save = useMutation({
    mutationFn: async () => {
      const result = account.id ? await api.updateAccount(account.id, { email, url, ...(key ? { key } : {}) }) : await api.addAccount({ email, key, url })
      if (account.id && status !== account.status && status !== 'error') await api.accountAction(account.id, status === 'active' ? 'enable' : 'disable')
      return result
    },
    onSuccess: () => onSaved(),
  })
  const remove = useMutation({ mutationFn: () => api.deleteAccount(account.id), onSuccess: () => onSaved(true) })
  const busy = save.isPending || remove.isPending
  return <section className="panel account-editor" role="dialog" aria-modal="true" aria-labelledby="account-title">
    <div className="section-heading"><h2 id="account-title">{account.id ? '编辑账号' : '添加账号'}</h2><button className="button" onClick={onClose} disabled={busy} aria-label="关闭账号表单"><X size={16} /></button></div>
    <form onSubmit={(event) => { event.preventDefault(); if (!busy) save.mutate() }}>
      <fieldset disabled={busy}>
        <label>显示邮箱<input value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus autoComplete="username" /></label>
        <label>API Key<input type="password" autoComplete="new-password" value={key} onChange={(event) => setKey(event.target.value)} required={!account.id} placeholder={account.id ? '留空保持不变' : '输入 CDS API Key'} /></label>
        <label>API 地址<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} required /></label>
        <p className="helper">凭据保存在运行后台服务的机器上。</p>
        {account.id && <CardSelect<Account['status']> label="账号状态" showLabel value={status} onChange={setStatus}
          options={[
            { value: 'active', label: '可用' },
            { value: 'disabled', label: '已禁用' },
            ...(account.status === 'error' ? [{ value: 'error' as const, label: '保持连接异常状态' }] : []),
          ]} />}
      </fieldset>
      <ErrorNotice error={save.error || remove.error} />
      <div className="form-actions">{account.id ? <button type="button" className="button danger" disabled={busy} onClick={() => window.confirm('确认删除这个账号？') && remove.mutate()}>删除账号</button> : <span />}<div className="row-actions"><button type="button" className="button" disabled={busy} onClick={onClose}>返回</button><button className="button primary" disabled={busy || !email.trim() || (!key && !account.id)}>{save.isPending ? '保存中…' : '保存'}</button></div></div>
    </form>
  </section>
}
