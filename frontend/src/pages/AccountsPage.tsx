import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api, type Account } from '../lib/api'
import { ErrorNotice, Loading, formatDate } from '../components'

const accountLabels = { active: '可用', disabled: '已禁用', error: '连接异常' }
const emptyAccount: Account = { id: '', email: '', url: 'https://cds.climate.copernicus.eu/api', status: 'active', used_count: 0, fail_count: 0, last_used: null, last_error: null }
export default function AccountsPage() {
  const [open, setOpen] = useState<Account | null>(null)
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.accounts, refetchInterval: 10000 })
  const test = useMutation({ mutationFn: api.testAccount })
  const saved = () => {
    setOpen(null)
    void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    void queryClient.invalidateQueries({ queryKey: ['summary'] })
  }
  return <section className="page">
    <div className="page-heading"><div><h1>CDS 账号</h1><p>下载时自动选择可用账号。</p></div><button className="button primary" onClick={() => setOpen(emptyAccount)}><Plus size={17} />添加账号</button></div>
    <ErrorNotice error={accounts.error || test.error} />
    {test.data && <p role="status" className={`notice ${test.data.ok ? '' : 'error'}`}>{test.data.ok ? '账号连接正常。' : '连接失败，请检查账号及网络。'}</p>}
    {accounts.isPending ? <Loading /> : <div className="account-list">{accounts.data?.items.map((account) => <article className="panel account-card" key={account.id}>
      <div className="section-heading"><h2>{account.email}</h2><span className={`account-status ${account.status}`}>{accountLabels[account.status]}</span></div>
      <p className="helper">{account.url}</p><p>已使用 {account.used_count} 次 · 连续失败 {account.fail_count} 次</p>
      <div className="row-actions"><button className="button" disabled={test.isPending} onClick={() => test.mutate(account.id)}>{test.isPending && test.variables === account.id ? '测试中…' : '测试连接'}</button><button className="button" onClick={() => setOpen(account)}>编辑</button></div>
    </article>)}</div>}
    {accounts.data?.items.length === 0 && <div className="panel empty-state">暂无账号，添加 CDS API 账号后即可下载。</div>}
    {open && <div className="dialog-backdrop"><AccountEditor key={open.id || 'new'} account={open} onClose={() => setOpen(null)} onSaved={saved} /></div>}
  </section>
}
function AccountEditor({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void }) {
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
    onSuccess: onSaved,
  })
  const remove = useMutation({ mutationFn: () => api.deleteAccount(account.id), onSuccess: onSaved })
  const busy = save.isPending || remove.isPending
  return <section className="panel account-editor" role="dialog" aria-modal="true" aria-labelledby="account-title">
    <div className="section-heading"><h2 id="account-title">{account.id ? '编辑账号' : '添加账号'}</h2><button className="button" onClick={onClose} disabled={busy} aria-label="关闭账号表单"><X size={16} /></button></div>
    <form onSubmit={(event) => { event.preventDefault(); if (!busy) save.mutate() }}>
      <fieldset disabled={busy}>
        <label>显示邮箱<input value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus autoComplete="username" /></label>
        <label>API Key<input type="password" autoComplete="new-password" value={key} onChange={(event) => setKey(event.target.value)} required={!account.id} placeholder={account.id ? '留空保持不变' : '输入 CDS API Key'} /></label>
        <p className="helper">凭据保存在运行后台服务的机器上。</p>
        {account.id && <label>账号状态<select value={status} onChange={(event) => setStatus(event.target.value as Account['status'])}><option value="active">可用</option><option value="disabled">已禁用</option>{account.status === 'error' && <option value="error">保持连接异常状态</option>}</select></label>}
        <details className="advanced"><summary>更多信息</summary><label>API 地址<input value={url} onChange={(event) => setUrl(event.target.value)} required /></label>{account.id && <p className="helper">最后使用：{formatDate(account.last_used)}</p>}</details>
      </fieldset>
      <ErrorNotice error={save.error || remove.error} />
      <div className="form-actions">{account.id ? <button type="button" className="button danger" disabled={busy} onClick={() => window.confirm('确认删除这个账号？') && remove.mutate()}>删除账号</button> : <span />}<div className="row-actions"><button type="button" className="button" disabled={busy} onClick={onClose}>返回</button><button className="button primary" disabled={busy || !email.trim() || (!key && !account.id)}>{save.isPending ? '保存中…' : '保存'}</button></div></div>
    </form>
  </section>
}
