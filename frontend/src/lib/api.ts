export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'retry_wait' | 'cancelling' | 'cancelled'
export type Task = {
  id: string
  dataset_id: string
  request_payload: Record<string, unknown>
  filename: string
  output_path: string
  status: TaskStatus
  progress: number | null
  downloaded_bytes: number
  total_bytes: number | null
  retry_count: number
  max_retries: number
  next_retry_at: string | null
  error_message: string | null
  account_id: string | null
  created_at: string
}
export type Account = {
  id: string
  email: string
  url: string
  status: 'active' | 'disabled' | 'error'
  used_count: number
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
export type Settings = {
  database_path: string
  download: { output_dir: string; max_workers: number; max_retries: number; retry_delays: number[] }
  ai: { enabled?: boolean; model?: string }
}
export type Schema = { fields?: { name: string; values?: unknown[] }[] }
export type RequestBody = {
  dataset_id: string
  request_payload: Record<string, unknown>
  split_strategy: string
  output_dir?: string
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : ''
    // 校验错误可能带输入值，界面只显示通用提示。
    throw new Error(response.status === 422 ? '参数或任务状态无效，请核对后重试。' : detail || `请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}
const post = <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
export const api = {
  summary: () => request<Summary>('/api/v1/summary'),
  tasks: (params = '') => request<{ items: Task[]; total: number }>(`/api/v1/tasks${params}`),
  task: (id: string) => request<Task>(`/api/v1/tasks/${id}`),
  preview: (body: RequestBody) => post<{ items: { filename: string; output_path: string }[] }>('/api/v1/requests/preview', body),
  createTasks: (body: RequestBody) => post<{ items: Task[] }>('/api/v1/tasks', body),
  action: (id: string, action: 'cancel' | 'retry') => post<Task>(`/api/v1/tasks/${id}/${action}`),
  datasets: () => request<{ items: { id: string; title: string }[] }>('/api/v1/datasets'),
  schema: (id: string) => request<Schema>(`/api/v1/datasets/${encodeURIComponent(id)}/schema`),
  accounts: () => request<{ items: Account[] }>('/api/v1/accounts'),
  addAccount: (body: Record<string, string>) => post<Account>('/api/v1/accounts', body),
  updateAccount: (id: string, body: Record<string, string>) => request<Account>(`/api/v1/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteAccount: (id: string) => request(`/api/v1/accounts/${id}`, { method: 'DELETE' }),
  accountAction: (id: string, action: 'enable' | 'disable') => post<Account>(`/api/v1/accounts/${id}/${action}`),
  testAccount: (id: string) => post<{ ok: boolean; message: string }>(`/api/v1/accounts/${id}/test`),
  suggestion: (body: { field_schema: Schema; user_request: string }) => post<{ suggestion: Record<string, unknown> }>('/api/v1/ai/suggestions', body),
  settings: () => request<Settings>('/api/v1/settings'),
}
