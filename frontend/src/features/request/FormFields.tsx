import { type Field, type Constraints } from '../../lib/api'
import { type Payload } from '../../requestFields'
import ParameterField from './ParameterField'
import CommaOptionInput from './CommaOptionInput'
import GeoReferenceMap from './GeoReferenceMap'

export default function FormFields({ fields, values, onChange, constraints }: { fields: Field[]; values: Payload; onChange: (name: string, value: unknown) => void; constraints?: Constraints }) {
  const byName = new Map(fields.map((field) => [field.name, field]))
  const children = new Set(fields.flatMap((field) => field.children || []))
  const render = (field: Field, grouped = false, compact = false): React.ReactNode => {
    if (field.field_type === 'exclusive') {
      const selected = String(values[field.name] ?? field.default ?? '')
      return <section className="parameter-group" key={field.name} role="group" aria-label={field.label}><div className="field-title"><h3>{field.label}</h3></div><details className="choice-entry"><summary aria-label={field.label + " 直接输入"}>输入</summary><CommaOptionInput field={{ name: field.name, label: field.label, options: field.children!.map((name) => ({ value: name, label: field.titles?.[name] || byName.get(name)!.label })) }} value={selected} onChange={(value) => onChange(field.name, value)} /></details><div className="branch-options" role="radiogroup" aria-label={`${field.label}模式`}>{field.children!.map((name) => <label className={`choice-card ${selected === name ? 'selected' : ''}`} key={name}><input type="radio" name={`group-${field.name}`} checked={selected === name} onChange={() => onChange(field.name, name)} />{field.titles?.[name] || byName.get(name)!.label}</label>)}</div>{field.children!.includes(selected) && render(byName.get(selected)!, true)}{field.children!.some((name) => ['area', 'location'].includes(byName.get(name)!.field_type)) && !byName.get(selected)?.request_field && <GeoReferenceMap kind="area" global />}</section>
    }
    if (field.field_type === 'layout') return <section className="parameter-group" key={field.name}><h3>{field.label}</h3>{field.children!.map((name) => render(byName.get(name)!, grouped))}</section>
    if (!field.request_field && ['global', 'all_dates'].includes(field.name) && grouped) return <p className="helper" key={field.name}>{field.description || '使用数据集的完整可用范围。'}</p>
    return <ParameterField key={field.name} field={field} value={values[field.name]} grouped={grouped} compact={compact} onChange={(value) => onChange(field.name, value)} allowed={constraints?.source === 'online' ? constraints.constraints[field.name] : undefined} />
  }
  const roots = fields.filter((field) => !children.has(field.name))
  // 只组织明确命名的时间维度，不生成字段、默认值或请求参数。
  const timeNames = new Set(['year', 'years', 'month', 'months', 'day', 'days', 'time', 'times', 'hour', 'hours'])
  const timeFields = roots.filter((field) => field.request_field && timeNames.has(field.name) && ['choice', 'multiple'].includes(field.field_type))
  return <div className="form-field-grid">{roots.map((field) => {
    if (timeFields.length > 1 && timeFields.includes(field)) return field === timeFields[0] ? <section className="time-panel" key="time-fields" aria-label="时间参数"><h3>时间</h3><div className="time-fields">{timeFields.map((item) => render(item, false, true))}</div></section> : null
    return render(field)
  })}</div>
}
