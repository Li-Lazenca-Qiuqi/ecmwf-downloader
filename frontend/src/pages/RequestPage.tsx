import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Send, Loader2, ListFilter, FileText } from 'lucide-react'
import { api, type RequestBody } from '../lib/api'
import { ErrorNotice, Loading } from '../components'
import CardSelect from '../CardSelect'
import { defaultsFor, fieldErrors, activeValues, requestPayload, type Payload } from '../requestFields'
import FormFields from '../features/request/FormFields'
import DatasetPicker from '../features/request/DatasetPicker'
import AIParameterPanel from '../features/request/AIParameterPanel'
import RequestSizePanel from '../features/request/RequestSizePanel'
import RequestDetailsDialog from '../features/request/RequestDetailsDialog'
import RequestAccountPicker from '../features/request/RequestAccountPicker'

const sources = { cds: 'CDS · Copernicus', ncar: 'NCAR AWS ERA5', gdex: 'NCAR GDEX ERA5' }
const sourceOptions = Object.entries(sources).map(([value, label]) => ({ value: value as keyof typeof sources, label }))
const splitOptions = [
  { value: 'none', label: '不拆分' },
  { value: 'year', label: '按年' },
  { value: 'month', label: '按月' },
  { value: 'day', label: '按日' },
  { value: 'smart', label: '按份数智能拆分' },
]
const initialDatasets = { ncar: 'mirror-ncar-era5', gdex: 'mirror-ncar-gdex-era5', cds: 'reanalysis-era5-single-levels' }
export default function RequestPage() {
  const [source, setSource] = useState<keyof typeof sources>('cds')
  return <RequestEditor key={source} source={source} onSourceChange={setSource} />
}

function RequestEditor({ source, onSourceChange }: { source: keyof typeof sources; onSourceChange: (source: keyof typeof sources) => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [datasetInput, setDatasetInput] = useState(initialDatasets[source])
  const [datasetId, setDatasetId] = useState(initialDatasets[source])
  const [prefixInput, setPrefixInput] = useState('e5.oper.an.sfc/202401/')
  const [prefix, setPrefix] = useState('e5.oper.an.sfc/202401/')
  const [payload, setPayload] = useState<Payload>({})
  const [requestName, setRequestName] = useState('')
  const [accountDraft, setAccountDraft] = useState<{ multiple: boolean; ids: string[] }>()
  const [split, setSplit] = useState('none')
  const [splitCount, setSplitCount] = useState('2')
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [aiNotice, setAiNotice] = useState('')
  const [aiUndo, setAiUndo] = useState<{ payload: Payload; version: number } | null>(null)
  const initialized = useRef('')
  const version = useRef(0)
  const schema = useQuery({ queryKey: ['request-schema', datasetId, prefix], queryFn: () => api.schema(datasetId, false, prefix), enabled: !!datasetId, retry: false, staleTime: 300000 })
  const fileSource = schema.data?.capabilities?.file_selection ?? (source === 'ncar' || source === 'gdex')
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.accounts, enabled: !fileSource })
  const availableAccounts = (accounts.data?.items ?? []).filter(account => account.status === 'active')
    .sort((a, b) => a.today_used_count - b.today_used_count || a.email.localeCompare(b.email) || a.id.localeCompare(b.id))
  const fields = schema.data?.support_status === 'unavailable' ? [] : schema.data?.fields || []
  useEffect(() => {
    const identity = `${datasetId}/${schema.data?.revision || ''}`
    if (schema.data?.collection_id === datasetId && schema.data.fields.length && initialized.current !== identity) {
      const sameDataset = initialized.current.startsWith(`${datasetId}/`)
      initialized.current = identity
      version.current += 1
      if (!sameDataset) setPayload(defaultsFor(schema.data.fields))
      else { setAiNotice('字段定义已更新，已保留当前输入，请检查有效性或重置默认值。'); setAiUndo(null) }
      setSplit((current) => schema.data?.capabilities?.split_strategies.includes(current) ? current : 'none')
    }
  }, [schema.data, datasetId])
  const errors = fieldErrors(fields, payload)
  const loaded = !!fields.length && schema.data?.source !== 'error'
  const count = Number(splitCount)
  const countValid = split !== 'smart' || (/^\d+$/.test(splitCount) && Number.isSafeInteger(count) && count >= 2)
  const valid = loaded && countValid && !errors.length && datasetInput.trim() === datasetId && (!fileSource || prefixInput.trim() === prefix)
  const selection = activeValues(fields, payload)
  const compiled = requestPayload(fields, payload)
  const body: RequestBody = {
    dataset_id: datasetId, request_payload: compiled, split_strategy: split,
    ...(split === 'smart' && countValid ? { split_count: count } : {}),
    ...(schema.data?.revision ? { schema_revision: schema.data.revision, editor_values: selection } : {}),
  }
  const bodyKey = JSON.stringify(body)
  const [stableBody, setStableBody] = useState(bodyKey)
  useEffect(() => { const timer = setTimeout(() => setStableBody(bodyKey), 400); return () => clearTimeout(timer) }, [bodyKey])
  const preview = useQuery({ queryKey: ['request-preview', bodyKey], queryFn: () => api.preview(JSON.parse(bodyKey)), enabled: valid && stableBody === bodyKey, retry: false })
  const selectionKey = JSON.stringify({ datasetId, revision: schema.data?.revision, compiled })
  const [stableSelection, setStableSelection] = useState(selectionKey)
  useEffect(() => { const timer = setTimeout(() => setStableSelection(selectionKey), 600); return () => clearTimeout(timer) }, [selectionKey])
  const constraints = useQuery({ queryKey: ['request-constraints', selectionKey], queryFn: () => api.constraints(datasetId, compiled), enabled: loaded && !fileSource && stableSelection === selectionKey, retry: false })
  const constraintErrors = Object.entries(selection).flatMap(([name, value]) => {
    const field = fields.find((item) => item.name === name)
    if (!field?.options.length) return []
    if (split === 'day' && ['day', 'days'].includes(name) && preview.data?.warnings?.length) return []
    const allowed = constraints.data?.source === 'online' ? constraints.data.constraints[name] : undefined
    return allowed !== undefined && (Array.isArray(value) ? value : [value]).some((item) => !allowed.some((option) => option === item)) ? [`${name}：当前组合不符合数据集约束，请调整选择。`] : []
  })
  const currentPlan = valid && !preview.isError && stableBody === bodyKey ? preview.data : undefined
  const requestCount = currentPlan?.items.length ?? 1
  const multiple = requestCount > 1
  const availableIds = availableAccounts.map(account => account.id)
  const accountIds = (accountDraft?.multiple === multiple
    ? availableIds.filter(id => accountDraft.ids.includes(id)) : availableIds).slice(0, requestCount)
  const defaultName = schema.data?.title.trim() || datasetId
  const create = useMutation({
    mutationFn: () => api.createTasks({
      ...body, name: requestName.trim() || defaultName,
      ...(!fileSource ? { account_ids: accountIds } : {}),
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
      navigate('/tasks')
    },
  })
  const suggestion = useMutation({
    mutationFn: async (snapshot: { version: number; datasetId: string; prompt: string; payload: Payload }) => {
      if (!schema.data) throw new Error('请先获取数据集字段。')
      const result = await api.suggestion({ field_schema: { ...schema.data, current_selection: snapshot.payload }, user_request: snapshot.prompt })
      if (snapshot.version !== version.current) return { snapshot, candidate: {} as Payload }
      const candidate = result.suggestion.parameters || result.suggestion.request_payload || result.suggestion
      if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) throw new Error('AI 未返回有效的参数对象。')
      const validation = fieldErrors(fields, candidate as Payload, false)
      if (validation.length) throw new Error(`AI 建议未应用：${validation.join(' ')}`)
      if (!Object.keys(candidate).length) throw new Error('AI 未给出可用参数，请补充需求后重试。')
      return { snapshot, candidate: candidate as Payload }
    },
    onSuccess: ({ snapshot, candidate }) => {
      if (snapshot.version !== version.current) { setAiNotice('需求、参数或数据集已改变，未应用过期的 AI 建议。'); return }
      create.reset()
      setPayload((current) => ({ ...current, ...candidate }))
      version.current += 1
      setAiUndo({ payload: snapshot.payload, version: version.current })
      setAiNotice(`已回填 ${Object.keys(candidate).length} 个参数，请检查字段和下方请求预览。`)
    },
  })
  const editParameters = () => {
    version.current += 1
    setAiUndo(null); setAiNotice('')
    if (!suggestion.isPending) suggestion.reset()
  }
  const changeField = (name: string, value: unknown) => {
    editParameters()
    create.reset()
    setPayload((current) => {
      const next = { ...current }
      if (value === undefined || Array.isArray(value) && !value.length) delete next[name]
      else next[name] = value
      if (fields.find((field) => field.name === name)?.field_type === 'exclusive' && typeof value === 'string' && next[value] === undefined) {
        const defaultValue = fields.find((field) => field.name === value)?.default
        if (defaultValue !== undefined && defaultValue !== null) next[value] = structuredClone(defaultValue)
      }
      return next
    })
  }
  const loadDataset = (selectedId?: string) => {
    const next = (selectedId ?? datasetInput).trim()
    if (!next) return
    setDatasetInput(next)
    version.current += 1
    setAiUndo(null)
    suggestion.reset(); create.reset(); setAiNotice('')
    if (next !== datasetId) { initialized.current = ''; setPayload({}); setSplit('none'); setDatasetId(next) }
    else void queryClient.fetchQuery({ queryKey: ['request-schema', next, prefix], queryFn: () => api.schema(next, true, prefix), staleTime: 0 })
  }
  const requestNames = new Set(fields.filter((field) => field.request_field).map((field) => field.name))
  const canSplit = (strategy: string) => {
    if (schema.data?.capabilities) return schema.data.capabilities.split_strategies.includes(strategy)
    if (strategy === 'smart') return false
    const dimensions = strategy === 'year' ? ['year'] : strategy === 'month' ? ['year', 'month'] : ['year', 'month', 'day']
    return dimensions.every(name => requestNames.has(name) || requestNames.has(`${name}s`))
  }
  const constraintsReady = stableSelection === selectionKey && !constraints.isFetching && (!!constraints.data || constraints.isError)
  const planReady = !!currentPlan && !schema.isFetching && !preview.isFetching
  const canCreate = planReady && (fileSource || (accountIds.length > 0 && !constraintErrors.length && (multiple || constraintsReady)))
  return <section className="page request-builder-page">
    <div className="page-heading request-heading">
      <div><h1>提交请求</h1><p>选择数据集和参数，提交后自动监视处理状态。</p></div>
      <CardSelect className="request-source-label" label="数据来源" showLabel value={source} options={sourceOptions} onChange={onSourceChange} />
    </div>
    <form id="download-request-form" className="request-builder-layout" onSubmit={(event) => { event.preventDefault(); if (canCreate && !create.isPending) create.mutate() }}><section className="panel request-form">
      <fieldset disabled={create.isPending}>
        <DatasetPicker source={source} value={datasetInput} onChange={(value) => { setDatasetInput(value); editParameters() }} onSelect={loadDataset}
          actions={<button type="button" className="button" disabled={!datasetInput.trim() || schema.isFetching} onClick={() => loadDataset()}>{schema.isFetching ? <Loader2 size={16} className="spin" /> : <ListFilter size={16} />}获取字段</button>} />
        {datasetInput.trim() !== datasetId && <p className="notice">请获取所选数据集的字段后继续。</p>}
        {fileSource && <div className="ncar-directory"><label>产品与年月目录<div className="directory-address"><input aria-label="NCAR 目录" value={prefixInput} onChange={(event) => { setPrefixInput(event.target.value); editParameters() }} placeholder="e5.oper.an.sfc/202401/" /><button type="button" className="button" disabled={schema.isFetching || !prefixInput.trim()} onClick={() => { editParameters(); initialized.current = ''; setPayload({}); if (prefixInput.trim() === prefix) loadDataset(); else setPrefix(prefixInput.trim()) }}>列出文件</button></div></label><details className="field-help"><summary>目录格式</summary><p className="helper">地表：e5.oper.an.sfc/YYYYMM/；压力层：e5.oper.an.pl/YYYYMM/。每个已发布文件生成一个请求。</p></details>{prefixInput.trim() !== prefix && <p className="notice">目录已修改，请重新列出文件后继续。</p>}</div>}
        <section className="request-parameters"><div className="section-heading"><h2>请求字段{loaded && <span className="field-source">{fields.filter((field) => field.request_field).length} 项 · {schema.data?.source === "cache" ? schema.data.stale ? "过期缓存" : "缓存字段" : "在线字段"}</span>}</h2><button type="button" className="text-button" disabled={!loaded} onClick={() => { editParameters(); setPayload(defaultsFor(fields)); create.reset() }}>重置默认值</button></div>{schema.isPending ? <Loading /> : <>
          <ErrorNotice error={schema.error} />{schema.data?.error && <p className="notice">{schema.data.error}</p>}

          {schema.data?.support_status === 'partial' && <p className="notice">部分字段尚待适配，可使用已支持的选择路径。</p>}
          {schema.data?.diagnostics?.filter((item) => item.blocking).map((item) => <p className="notice error" key={`${item.code}/${item.field}`}>{item.message}</p>)}
          <FormFields key={`${datasetId}/${schema.data?.revision || ""}`} fields={fields} values={payload} onChange={changeField} constraints={constraints.data} />
          {constraints.data?.error && <p className="notice">{constraints.data.error}</p>}
          {constraints.error && <p className="notice">约束服务暂不可用，当前只做本地检查，最终是否接受请求以数据来源响应为准。</p>}
          {constraintErrors.map((message) => <p className="notice error" key={message}>{message}</p>)}
        </>}</section>

      </fieldset>

    </section>
    <aside className="request-assistance" aria-label="参数补全与提交">
      <div className="request-assistance-scroll">
        <fieldset className="request-assistance-controls" disabled={create.isPending}>
          <AIParameterPanel ready={loaded && datasetInput.trim() === datasetId && !schema.isFetching && (!fileSource || prefixInput.trim() === prefix)} pending={suggestion.isPending} error={suggestion.error} notice={aiNotice} canUndo={!!aiUndo && aiUndo.version === version.current}
            onEdit={editParameters} onGenerate={(prompt) => { setAiNotice(''); setAiUndo(null); suggestion.mutate({ version: version.current, datasetId, prompt, payload: selection }) }}
            onUndo={() => { if (aiUndo?.version === version.current) { setPayload(aiUndo.payload); version.current += 1; setAiUndo(null); setAiNotice('已恢复补全前的参数。'); create.reset() } }} />
        </fieldset>
        <section className="panel request-output" aria-label="请求拆分与提交">
          <h2>请求拆分与提交</h2>
          <fieldset disabled={create.isPending}>
            <label className="request-name">请求名称
              <input value={requestName} placeholder={defaultName}
                onChange={event => { setRequestName(event.target.value); create.reset() }} />
            </label>
            <section className="output-section" aria-label="请求拆分">
              <CardSelect label="拆分方式" showLabel value={split} onChange={value => { setSplit(value); create.reset() }}
                options={splitOptions.map(option => option.value === 'none' || canSplit(option.value) ? option : {
                  ...option, label: `${option.label}（当前数据集不支持）`, disabled: true,
                })} />
              {split === 'smart' && <label className="split-count">目标份数
                <input type="number" min={2} step={1} value={splitCount} aria-invalid={!countValid}
                  onChange={event => { setSplitCount(event.target.value); create.reset() }} />
              </label>}
              {!countValid && <p className="inline-error" role="alert">请输入大于等于 2 的整数份数。</p>}
            </section>
            {!fileSource && <RequestAccountPicker accounts={availableAccounts} selected={accountIds}
              limit={requestCount} loading={accounts.isPending} error={accounts.error}
              onChange={ids => { setAccountDraft({ multiple, ids }); create.reset() }} />}
          </fieldset>
          {errors.length > 0 && loaded && <details className="validation-list">
            <summary>待补齐 {errors.length} 项参数</summary>
            {errors.map(message => <p key={message}>{message}</p>)}
          </details>}
          <ErrorNotice error={preview.error} />
          {currentPlan?.warnings?.map(message => <p className="notice" key={message}>{message}</p>)}
          {source === 'cds' && <RequestSizePanel body={body} ready={planReady} disabled={create.isPending} />}
          <ErrorNotice error={create.error} />
          <div className="form-actions"><button type="submit" className="button primary" disabled={!canCreate || create.isPending}>{create.isPending ? <Loader2 size={16} className="spin" /> : <Send size={16} />}{preview.isFetching ? '计算拆分…' : currentPlan && multiple ? `提交 ${requestCount} 个请求` : '提交请求'}</button><Link className="button" to="/tasks">返回队列</Link></div>
        </section>
      </div>
      <div className="panel request-details-footer">
        <button type="button" className="button" aria-haspopup="dialog" aria-expanded={detailsOpen} onClick={() => setDetailsOpen(true)}><FileText size={15} aria-hidden="true" />显示请求详情</button>
      </div>
      {detailsOpen && <RequestDetailsDialog datasetId={datasetId} items={currentPlan?.items ?? []} draft={compiled} fields={fields} onClose={() => setDetailsOpen(false)} />}
    </aside></form>
  </section>
}
