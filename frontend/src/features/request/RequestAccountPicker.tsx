import CardSelect from '../../CardSelect'
import { ErrorNotice } from '../../components'
import { type Account } from '../../lib/api'

export default function RequestAccountPicker({ accounts, selected, limit, loading, error, onChange }: {
  accounts: Account[]
  selected: string[]
  limit: number
  loading: boolean
  error: unknown
  onChange: (ids: string[]) => void
}) {
  if (loading) return <p className="request-account-picker" role="status">加载账号…</p>
  if (error) return <ErrorNotice error={error} />
  if (!accounts.length) return <p className="inline-error">无可用 CDS 账号</p>
  return <section className="request-account-picker" aria-label="提交账号">
    {limit === 1 ? <CardSelect label="提交账号" showLabel value={selected[0] ?? ''}
        options={accounts.map(account => ({
          value: account.id, label: `${account.email} · 今日 ${account.today_used_count} 次`,
        }))}
        onChange={id => onChange([id])} />
      : <fieldset>
        <legend>提交账号</legend>
        <div className="request-account-options">
          {accounts.map(account => {
            const checked = selected.includes(account.id)
            return <label className="choice-card" key={account.id}>
              <input type="checkbox" checked={checked} disabled={!checked && selected.length >= limit}
                onChange={event => onChange(event.target.checked
                  ? [...selected, account.id] : selected.filter(id => id !== account.id))} />
              <span>{account.email}</span><span className="account-usage">今日 {account.today_used_count} 次</span>
            </label>
          })}
        </div>
        {selected.length === 0 && <p className="inline-error">请选择提交账号</p>}
      </fieldset>}
  </section>
}
