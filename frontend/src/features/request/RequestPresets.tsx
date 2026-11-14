import { useId, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Field, type Schema, type Template } from '../../lib/api'
import { ErrorNotice } from '../../components'
import RequestPresetDialog from './RequestPresetDialog'
import { requestSchemaFreshMs, requestSchemaKey } from './requestOptions'
import { activeFields, fieldErrors, type Payload } from '../../requestFields'

const presetsKey = ['request-presets'] as const

export type RequestSource = 'cds' | 'ncar' | 'gdex'
export type Preset = {
  kind: 'ecmwf-request-preset-v1'
  source: RequestSource
  dataset_id: string
  prefix: string
  editor_values: Payload
  split_strategy: string
  split_count?: number
}

function isPreset(payload: Record<string, unknown>): payload is Preset {
  return payload.kind === 'ecmwf-request-preset-v1'
    && ['cds', 'ncar', 'gdex'].some(source => source === payload.source)
    && typeof payload.dataset_id === 'string' && typeof payload.prefix === 'string'
    && !!payload.editor_values && typeof payload.editor_values === 'object' && !Array.isArray(payload.editor_values)
    && typeof payload.split_strategy === 'string'
}

export function restorePresetValues(fields: Field[], saved: Payload) {
  const values: Payload = {}
  const changes = new Set<string>()
  for (const { field } of activeFields(fields, saved)) {
    const value = saved[field.name]
    if (value === undefined || (!field.request_field && field.field_type !== 'exclusive')) continue
    if (field.field_type === 'exclusive' && !field.children?.includes(String(value))) {
      changes.add(field.label)
      continue
    }
    if (field.field_type === 'multiple' && field.options.length && Array.isArray(value)) {
      const allowed = new Set(field.options.map(option => option.value))
      const filtered = value.filter(item => allowed.has(item))
      if (filtered.length < value.length) changes.add(field.label)
      if (filtered.length) values[field.name] = filtered
      continue
    }
    const detached = { ...field, children: undefined }
    if (field.field_type !== 'exclusive' && fieldErrors([detached], { [field.name]: value }, false).length) {
      changes.add(field.label)
    } else values[field.name] = value
  }
  const known = new Set(fields.map(field => field.name))
  for (const name of Object.keys(saved)) if (!known.has(name)) changes.add(name)
  return { values, changes: [...changes] }
}

export default function RequestPresets({ preset, canSave, disabled, onLoad, onSaved, children }: {
  preset: Preset
  canSave: boolean
  disabled: boolean
  onLoad: (preset: Preset) => void
  onSaved: () => void
  children: ReactNode
}) {
  const saveFormId = useId()
  const client = useQueryClient()
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const templates = useQuery({ queryKey: presetsKey, queryFn: api.templates })
  const presets = (templates.data?.items ?? []).flatMap(item =>
    isPreset(item.payload) ? [{ id: item.id, name: item.name, preset: item.payload }] : [],
  )
  const save = useMutation({
    mutationFn: () => api.saveTemplate(name.trim(), preset),
    onSuccess: () => {
      setSaving(false)
      setName('')
      onSaved()
      void client.invalidateQueries({ queryKey: presetsKey })
    },
  })
  const load = useMutation({
    mutationFn: async (saved: Preset) => {
      const key = requestSchemaKey(saved.dataset_id, saved.prefix)
      const cached = client.getQueryState<Schema>(key)
      if (cached?.data?.fields.length && cached.data.source !== 'error'
        && cached.data.support_status !== 'unavailable' && !cached.data.stale
        && !cached.isInvalidated && Date.now() - cached.dataUpdatedAt < requestSchemaFreshMs) {
        return saved
      }

      const schema = await api.schema(saved.dataset_id, false, saved.prefix)
      if (!schema.fields.length || schema.source === 'error' || schema.support_status === 'unavailable') {
        throw new Error(schema.error || '无法获取预设的数据集字段，请稍后重试。')
      }
      client.setQueryData(key, schema)
      return saved
    },
    onSuccess: onLoad,
  })
  const remove = useMutation({
    mutationFn: api.deleteTemplate,
    onSuccess: async (_, id) => {
      await client.cancelQueries({ queryKey: presetsKey })
      client.setQueryData<{ items: Template[] }>(presetsKey, current =>
        current && { items: current.items.filter(item => item.id !== id) },
      )
      void client.invalidateQueries({ queryKey: presetsKey })
    },
  })
  return <div className="request-presets">
    <div className="request-submit-actions">
      <button type="button" className="button" aria-haspopup="dialog" aria-expanded={loading}
        disabled={disabled || save.isPending} onClick={() => { load.reset(); remove.reset(); setLoading(true) }}>加载预设</button>
      <button type="button" className="button" disabled={disabled || !canSave || load.isPending}
        aria-expanded={saving} onClick={() => { setSaving(value => !value); save.reset() }}>保存预设</button>
      {children}
    </div>
    {saving && <>
      {createPortal(<form id={saveFormId} onSubmit={event => {
        event.preventDefault()
        event.stopPropagation()
        const existing = templates.data?.items.find(item => item.name === name.trim())
        if (existing && isPreset(existing.payload) && !window.confirm(`覆盖预设「${existing.name}」？`)) return
        if (canSave && !disabled && name.trim() && !save.isPending && templates.isSuccess) save.mutate()
      }} />, document.body)}
      <div className="row-actions preset-save-fields">
        <input form={saveFormId} aria-label="预设名称" placeholder="预设名称" value={name} onChange={event => setName(event.target.value)} required />
        <button form={saveFormId} type="submit" className="button" disabled={disabled || !canSave || !name.trim() || save.isPending || !templates.isSuccess}>保存</button>
      </div>
    </>}
    {loading && <RequestPresetDialog presets={presets} pending={templates.isPending} applying={load.isPending}
      removing={remove.isPending} error={load.error || remove.error || templates.error} onClose={() => setLoading(false)}
      onSelect={() => { load.reset(); remove.reset() }}
      onApply={preset => { remove.reset(); load.mutate(preset) }}
      onDelete={id => { load.reset(); remove.mutate(id) }} />}
    <ErrorNotice error={save.error} />
  </div>
}
