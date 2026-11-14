import CardSelect from '../../CardSelect'
import { ErrorNotice } from '../../components'
import { type Account } from '../../lib/api'

export default function RequestAccountPicker({ accounts, selected, limit, loading, error, busySelection, onChange }: {
  accounts: Account[]
  selected: string[]
  limit: number
  loading: boolean
  error: unknown
  busySelection: boolean
  onChange: (ids: string[]) => void
}) {
  if (loading) return <p className="request-account-picker" role="status">加载账号…</p>
  if (error) return <ErrorNotice error={error} />
  if (!accounts.length) return <p className="inline-error">无可用 CDS 账号</p>
  const idle = accounts.some(account => !account.is_busy)
  return <section className="request-account-picker" aria-label="提交账号">
    {limit === 1 ? <CardSelect label="提交账号" showLabel value={selected[0] ?? ''}
        options={accounts.map(account => ({
          value: account.id, label: `${account.email} · ${account.is_busy ? "繁忙" : `今日 ${account.today_used_count} 次`}`,
          disabled: account.is_busy,
        }))}
        onChange={id => onChange([id])} />
      : <fieldset>
        <legend>提交账号</legend>
        <div className="request-account-options">
          {accounts.map(account => {
            const checked = selected.includes(account.id)
            return <label className="choice-card" key={account.id}>
              <input type="checkbox" checked={checked} disabled={account.is_busy || (!checked && selected.length >= limit)}
                onChange={event => onChange(event.target.checked
                  ? [...selected, account.id] : selected.filter(id => id !== account.id))} />
              <span>{account.email}</span><span className="account-usage">{account.is_busy ? "繁忙" : `今日 ${account.today_used_count} 次`}</span>
            </label>
          })}
        </div>
      </fieldset>}
    {idle && busySelection && <p className="inline-error">所选账号已繁忙，请重新选择。</p>}
    {!idle ? <p className="inline-error">暂无空闲 CDS 账号</p> : !selected.length && !busySelection && <p className="inline-error">请选择提交账号</p>}
  </section>
}
