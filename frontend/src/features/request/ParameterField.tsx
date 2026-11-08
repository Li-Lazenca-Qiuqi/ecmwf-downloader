import { useId } from 'react'
import { CircleHelp } from 'lucide-react'
import { type Field } from '../../lib/api'
import OptionPicker from './OptionPicker'
import ChoicePicker from './ChoicePicker'
import FilePicker from './FilePicker'
import FreeListInput from './FreeListInput'
import GeoReferenceMap from './GeoReferenceMap'

export default function ParameterField({ field, value, onChange, allowed, grouped = false, compact = false }: { field: Field; value: unknown; onChange: (value: unknown) => void; allowed?: unknown[]; grouped?: boolean; compact?: boolean }) {
  const modeId = useId()
  const label = `${field.label} (${field.name})`
  if (!field.request_field) return <details className="field-information"><summary>{field.label}</summary><p className="helper">{field.description || '此项为表单说明，不作为请求参数提交。'}</p>{field.licences?.map((licence) => <p key={licence.id}>{licence.attachment_url?.startsWith('https://') ? <a href={licence.attachment_url} target="_blank" rel="noreferrer">{licence.label}</a> : licence.label}</p>)}</details>
  let control
  if (field.presentation === 'files') control = <FilePicker field={field} value={value} onChange={onChange} />
  else if (field.field_type === 'multiple' && field.options.length) control = <OptionPicker compact={compact} field={field} value={value} onChange={onChange} allowed={allowed} />
  else if (field.field_type === 'choice') control = <ChoicePicker compact={compact} field={field} value={value} onChange={onChange} allowed={allowed} />
  else if (field.field_type === 'area' || field.field_type === 'location') {
    const point = field.field_type === 'location'
    const coordinates = Array.isArray(value) ? value : undefined
    const names = point ? ['Latitude', 'Longitude'] : ['North', 'West', 'South', 'East']
    const range = field.bounds?.range || { n: 90, w: -180, s: -90, e: 180 }
    const entries = coordinates || (Array.isArray(field.default) ? field.default : names.map(() => null))
    const show = point || grouped || field.required || !!coordinates
    control = <>{!point && !grouped && !field.required && <div className="region-mode" role="radiogroup" aria-label={`${field.label}选择`}><label className="choice-card"><input type="radio" name={modeId} checked={!coordinates} onChange={() => onChange(undefined)} />全部范围</label><label className="choice-card"><input type="radio" name={modeId} checked={!!coordinates} onChange={() => onChange(Array.isArray(field.default) ? [...field.default] : [90, -180, -90, 180])} />自定义区域</label></div>}{show ? <div className="coordinates">{names.map((name, index) => <label key={name}>{name}<input type="number" aria-label={`${field.name} ${name}`} step="any" min={index % 2 ? range.w : range.s} max={index % 2 ? range.e : range.n} value={entries[index] ?? ''} onChange={(event) => { const next = [...entries]; next[index] = event.target.value === '' ? null : Number(event.target.value); onChange(next) }} /></label>)}</div> : <p className="helper">使用数据集的完整可用范围。</p>}{(field.bounds?.minimum_extent || field.bounds?.maximum_extent) && <p className="helper">{field.bounds.minimum_extent && `最小区域：${field.bounds.minimum_extent.lat}° × ${field.bounds.minimum_extent.lon}°`}{field.bounds.maximum_extent && ` 最大区域：${field.bounds.maximum_extent.lat}° × ${field.bounds.maximum_extent.lon}°`}</p>}<GeoReferenceMap kind={point ? "location" : "area"} coordinates={show ? entries : undefined} range={range} global={!show} /></>
  } else if (field.field_type === 'date_range') {
    const dates = Array.isArray(value) ? value : ['', '']
    const monthly = field.bounds?.time_resolution === 'monthly'
    control = <div className="coordinates">{['开始日期', '结束日期'].map((name, index) => <label key={name}>{name}<input type={monthly ? 'month' : 'date'} aria-label={`${field.name} ${name}`} value={dates[index] || ''} min={field.bounds?.minStart?.slice(0, monthly ? 7 : 10)} max={field.bounds?.maxEnd?.slice(0, monthly ? 7 : 10)} onChange={(event) => { const next = [...dates]; next[index] = event.target.value; onChange(next) }} /></label>)}</div>
  } else if (field.field_type === 'object') {
    const object = (value || {}) as Record<string, unknown>
    control = <div className="object-fields">{Object.values(field.properties || {}).map((child) => <ParameterField key={child.name} field={child} value={object[child.name]} onChange={(next) => { const updated = { ...object }; if (next === undefined) delete updated[child.name]; else updated[child.name] = next; onChange(updated) }} />)}</div>
  } else if (field.field_type === 'number') control = <input type="number" aria-label={label} min={field.minimum} max={field.maximum} step={field.integer ? 1 : 'any'} value={typeof value === 'number' ? value : ''} onChange={(event) => onChange(event.target.value === '' ? undefined : Number(event.target.value))} />
  else if (field.field_type === 'boolean') control = <ChoicePicker field={{ ...field, options: [{ value: true, label: '是' }, { value: false, label: '否' }] }} value={value} onChange={onChange} />
  else if (field.field_type === 'multiple') control = <FreeListInput field={field} value={value} onChange={onChange} />
  else if (field.field_type === 'text') control = <input aria-label={label} value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value || undefined)} />
  else control = <p className="notice">此字段的 {field.widget || field.field_type} 控件尚未支持。{field.required || grouped ? '需要支持此字段后才能提交。' : '不设置此项时可使用其他已支持字段。'}</p>
  return <section className="parameter-field" data-compact={['choice', 'multiple'].includes(field.field_type) && field.options.length <= 100 && !(field.field_type === 'multiple' && field.options.length <= 4) && !field.options.some((option) => option.group || option.groups?.length) && field.presentation !== 'files'} role="group" aria-label={label}><div className="field-title"><h3>{field.label}</h3><code>{field.name}</code>{field.description && <details className="field-help"><summary aria-label={field.label + " 说明"} title="说明"><CircleHelp size={13} /></summary><p className="helper">{field.description}</p></details>}{(field.required || grouped) && <small aria-label="必填">*</small>}</div>{control}</section>
}
