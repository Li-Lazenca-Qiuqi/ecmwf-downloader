import { useState } from 'react'
import { type Field } from '../../lib/api'
import RequestPreviewCode from './RequestPreviewCode'

function ParameterValue({ value, field }: { value: unknown; field?: Field }) {
  const labels = new Map<unknown, string>(field?.options.map(option => [option.value, option.label]))
  const format = (entry: unknown) => labels.get(entry) ?? (typeof entry === 'boolean' ? (entry ? '是' : '否') : String(entry ?? '空值'))

  if (Array.isArray(value)) {
    if (!value.length) return <span>空列表</span>
    if (field?.field_type === 'area' && value.length === 4) {
      return <dl className="request-parameter-properties">{['北界', '西界', '南界', '东界'].map((label, i) => <div key={label}><dt>{label}</dt><dd>{format(value[i])}</dd></div>)}</dl>
    }
    return <ul className="request-parameter-values">{value.map((entry, i) => <li key={i}>
      {entry !== null && typeof entry === 'object' ? <ParameterValue value={entry} /> : format(entry)}
    </li>)}</ul>
  }
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value)
    if (!entries.length) return <span>无子参数</span>
    return <dl className="request-parameter-properties">{entries.map(([name, entry]) => <div key={name}>
      <dt>{field?.properties?.[name]?.label ?? name}</dt>
      <dd><ParameterValue value={entry} field={field?.properties?.[name]} /></dd>
    </div>)}</dl>
  }
  return <span>{format(value)}</span>
}

function RequestParameterCards({ payload, fields }: { payload: Record<string, unknown>; fields: Field[] }) {
  const entries = Object.entries(payload)
  const definitions = new Map(fields.map(field => [field.name, field]))
  if (!entries.length) return <p className="helper">尚未选择请求参数。</p>

  return <dl className="request-parameter-cards" aria-label="已选请求参数">
    {entries.map(([name, value]) => {
      const field = definitions.get(name)
      return <div className="request-parameter-card" key={name}>
        <dt>{field?.label ?? name}{field?.label && field.label !== name && <code>{name}</code>}</dt>
        <dd><ParameterValue value={value} field={field} /></dd>
      </div>
    })}
  </dl>
}

export default function RequestParameterViews({ payload, fields = [], payloadIndex, heading }: {
  payload: Record<string, unknown>
  fields?: Field[]
  payloadIndex?: number
  heading?: string
}) {
  const [view, setView] = useState<'cards' | 'json'>('cards')

  return <>
    <div className="request-parameter-toolbar">
      {heading && <h3>{heading}</h3>}
      <div className="request-details-views" role="group" aria-label="参数视图">
        <button type="button" className="button" aria-pressed={view === 'cards'} onClick={() => setView('cards')}>卡片视图</button>
        <button type="button" className="button" aria-pressed={view === 'json'} onClick={() => setView('json')}>JSON</button>
      </div>
    </div>
    {view === 'cards'
      ? <RequestParameterCards key={payloadIndex} payload={payload} fields={fields} />
      : <RequestPreviewCode key={payloadIndex} payload={payload} />}
  </>
}
