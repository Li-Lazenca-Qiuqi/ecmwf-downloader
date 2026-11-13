export type TaskStatus = 'queued' | 'submitting' | 'accepted' | 'running' | 'refreshing' | 'completed' | 'failed' | 'cancelling' | 'cancelled' | 'expired' | 'submission_unknown'
export type ResultAsset = { url: string; filename: string | null; size: number | null; content_type: string | null; expires_at: string | null }
export type Task = {
  id: string
  dataset_id: string
  request_payload: Record<string, unknown>
  title: string
  batch?: { batch_id: string; name: string; position: number; total: number } | null
  status: TaskStatus
  remote_request_id: string | null
  remote_status: string | null
  results: ResultAsset[]
  checked_at: string | null
  retry_count: number
  max_retries: number
  next_retry_at: string | null
  error_message: string | null
  account_id: string | null
  submission_account_id?: string | null
  cancel_requested: boolean
  created_at: string
}
export type Template = { id: string; name: string; payload: Record<string, unknown> }
export type Account = {
  id: string
  email: string
  url: string
  status: 'active' | 'disabled' | 'error'
  is_busy: boolean
  used_count: number
  today_used_count: number
  fail_count: number
  last_used: string | null
  last_error: string | null
}
export type Summary = {
  total: number
  by_status: Partial<Record<TaskStatus, number>>
  active_workers: number
  max_workers: number | null
  available_accounts: number
  scheduler_running: boolean
}
export type NetworkProxyConfig = { mode: 'direct' | 'system' | 'manual'; url: string }
export type Settings = {
  network_proxy: NetworkProxyConfig
  ai_config: AIConfig
  database_path: string
  requests: { max_workers: number; max_retries: number; retry_delays: number[]; poll_interval: number }
  ai: { enabled?: boolean; model?: string }
}
export type Field = {
  name: string; label: string; field_type: string; required: boolean; request_field: boolean
  options: { value: string | number | boolean; label: string; group?: string; groups?: string[] }[]
  default?: unknown; description?: string; integer?: boolean; item_type?: string; widget?: string; minimum?: number; maximum?: number; step?: number | 'any'
  children?: string[]; titles?: Record<string, string>; wire_type?: string | null; presentation?: string
  bounds?: { range?: { n: number; w: number; s: number; e: number }; minimum_extent?: Record<string, number>; maximum_extent?: Record<string, number>; stepX?: number; stepY?: number; minStart?: string; maxEnd?: string; time_resolution?: string }
  properties?: Record<string, Field>; open_groups?: string[]; licences?: { id: string; label: string; attachment_url?: string }[]
}
export type Schema = { collection_id: string; title: string; fields: Field[]; source: 'online' | 'cache' | 'error'; stale?: boolean; error?: string | null; description?: string; source_url?: string; prefix?: string; revision?: string; support_status?: 'full' | 'partial' | 'unavailable'; diagnostics?: { code: string; field: string; message: string; blocking: boolean }[]; capabilities?: { split_strategies: string[]; file_selection: boolean; spatial_modes: string[] } }
export type Constraints = { constraints: Record<string, unknown[]>; source: 'online' | 'error' | 'not_applicable'; error?: string | null }
export type Costing = {
  source: 'online' | 'error' | 'not_applicable'; error?: string | null; id?: string; cost?: number; limit?: number | null
  request_count?: number; estimated_count?: number; max_index?: number; over_limit_count?: number
}
export type DatasetCatalogue = { items: { id: string; title: string }[]; total: number; catalogue_total: number; source: 'online' | 'cache' | 'error' | 'builtin'; stale: boolean; error: string | null; fetched_at: string | null }
export type AIConfig = { enabled: boolean; base_url: string; model: string; json_mode: boolean; has_api_key: boolean; sdk_available: boolean; ready: boolean }
export type AIConfigInput = Pick<AIConfig, 'enabled' | 'base_url' | 'model' | 'json_mode'> & { api_key?: string }
export type SettingsUpdate = {
  network_proxy?: NetworkProxyConfig
  ai?: Partial<Omit<AIConfigInput, 'api_key'>>
  requests?: Partial<Pick<Settings['requests'], 'poll_interval' | 'max_retries'>>
}
export type RequestBody = {
  dataset_id: string
  request_payload: Record<string, unknown>
  split_strategy: string
  split_count?: number
  schema_revision?: string
  editor_values?: Record<string, unknown>
}
export type RequestPreviewItem = { label: string; request_payload: Record<string, unknown> }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : ''
    // 校验错误可能带输入值，界面只显示通用提示。
    // 结构化校验错误可能包含输入，其他由后端生成的参数提示可以直接展示。
    throw new Error(response.status === 422 && detail.startsWith('[') ? '参数或任务状态无效，请核对后重试。' : detail || `请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}
const post = <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
export const api = {
  summary: () => request<Summary>('/api/v1/summary'),
  tasks: (params = '') => request<{ items: Task[]; total: number }>(`/api/v1/tasks${params}`),
  templates: () => request<{ items: Template[] }>('/api/v1/templates'),
  saveTemplate: (name: string, payload: Record<string, unknown>) =>
    post<Template>('/api/v1/templates', { name, payload }),
  deleteTemplate: (id: string) => request<{ deleted: boolean; id: string }>(
    `/api/v1/templates/${encodeURIComponent(id)}`, { method: 'DELETE' },
  ),
  task: (id: string) => request<Task>(`/api/v1/tasks/${id}`),
  preview: (body: RequestBody) => post<{ items: RequestPreviewItem[]; warnings: string[] }>('/api/v1/requests/preview', body),
  createTasks: (body: RequestBody & { name: string; account_ids?: string[] }) => post<{ items: Task[] }>('/api/v1/tasks', body),
  action: (id: string, action: 'cancel' | 'retry' | 'refresh') => post<Task>(`/api/v1/tasks/${id}/${action}`),
  deleteTask: (id: string) => request(`/api/v1/tasks/${id}`, { method: 'DELETE' }),
  attach: (id: string, remote_request_id: string) => post<Task>('/api/v1/tasks/' + id + '/attach', { remote_request_id }),
  datasets: (refresh = false, source = 'cds') => request<DatasetCatalogue>(`/api/v1/datasets?${new URLSearchParams({ refresh: String(refresh), source })}`),
  schema: (id: string, refresh = false, prefix = 'e5.oper.an.sfc/202401/') => request<Schema>(`/api/v1/datasets/${encodeURIComponent(id)}/schema?${new URLSearchParams({ refresh: String(refresh), prefix })}`),
  constraints: (id: string, selection: Record<string, unknown>) => post<Constraints>(`/api/v1/datasets/${encodeURIComponent(id)}/constraints`, selection),
  costing: (id: string, body: Omit<RequestBody, 'dataset_id'>) => post<Costing>(`/api/v1/datasets/${encodeURIComponent(id)}/costing`, body),
  accounts: () => request<{ items: Account[] }>('/api/v1/accounts'),
  addAccount: (body: Record<string, string>) => post<Account>('/api/v1/accounts', body),
  updateAccount: (id: string, body: Record<string, string>) => request<Account>(`/api/v1/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteAccount: (id: string) => request(`/api/v1/accounts/${id}`, { method: 'DELETE' }),
  accountAction: (id: string, action: 'enable' | 'disable') => post<Account>(`/api/v1/accounts/${id}/${action}`),
  testAccount: (id: string) => post<{ ok: boolean; message: string }>(`/api/v1/accounts/${id}/test`),
  suggestion: (body: { field_schema: Schema & { current_selection?: Record<string, unknown> }; user_request: string }) => post<{ suggestion: Record<string, unknown> }>('/api/v1/ai/suggestions', body),
  aiConfig: () => request<AIConfig>('/api/v1/ai/config'),
  testAIConfig: (body: AIConfigInput & { network_proxy?: NetworkProxyConfig }) => post<{ message: string }>('/api/v1/ai/test', body),
  settings: () => request<Settings>('/api/v1/settings'),
  settingsAIKey: (signal: AbortSignal) =>
    request<{ api_key: string }>('/api/v1/settings/ai-key', { signal, cache: 'no-store' }),
  saveSettings: (values: SettingsUpdate, ai_api_key?: string) =>
    request<Settings>('/api/v1/settings', { method: 'PATCH', body: JSON.stringify({ values, ai_api_key }) }),
  testNetworkProxy: (network: NetworkProxyConfig) =>
    post<{ ok: boolean; message: string }>('/api/v1/settings/network-proxy/test', network),
}
