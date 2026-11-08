import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api, type Account } from '../lib/api'
import { ErrorNotice, Loading, formatDate } from '../components'
import CardSelect from '../CardSelect'

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
    <div className="page-heading"><div><h1>CDS 账号</h1><p>提交 CDS 请求时自动选择可用账号，后续用同一账号查询结果。</p></div><button className="button primary" onClick={() => setOpen(emptyAccount)}><Plus size={17} />添加账号</button></div>
    <ErrorNotice error={accounts.error || test.error} />
    {test.data && <p role="status" className={`notice ${test.data.ok ? '' : 'error'}`}>{test.data.message}</p>}
    {accounts.isPending ? <Loading /> : <div className="panel table-scroll"><table className="account-table" aria-label="CDS 账号列表">
      <thead><tr><th scope="col">账号</th><th scope="col">API 地址</th><th scope="col">状态</th><th scope="col">使用次数</th><th scope="col">连续失败</th><th scope="col">最后使用</th><th scope="col">操作</th></tr></thead>
      <tbody>{accounts.data?.items.map((account) => <tr key={account.id}>
        <td className="account-email">{account.email}</td><td className="account-url">{account.url}</td>
        <td><span className={`account-status ${account.status}`}>{accountLabels[account.status]}</span></td>
        <td>{account.used_count}</td><td>{account.fail_count}</td><td className="date-cell">{formatDate(account.last_used)}</td>
        <td><div className="row-actions"><button className="button" disabled={test.isPending} onClick={() => test.mutate(account.id)}>{test.isPending && test.variables === account.id ? '测试中…' : '测试连接'}</button><button className="button" onClick={() => setOpen(account)}>编辑</button></div></td>
      </tr>)}{accounts.data?.items.length === 0 && <tr><td colSpan={7} className="empty-state">暂无账号。添加 CDS API 账号后可提交 CDS 请求。</td></tr>}</tbody>
    </table></div>}
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
