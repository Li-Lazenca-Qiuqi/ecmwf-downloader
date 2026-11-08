import { Loader2 } from 'lucide-react'
import { type TaskStatus } from './lib/api'

export const statusLabels: Record<TaskStatus, string> = {
  queued: '本地排队', submitting: '提交中', accepted: '远端排队', running: '远端处理中',
  refreshing: '更新链接', completed: '链接已就绪', failed: '失败', cancelling: '取消中',
  cancelled: '已取消', expired: '结果失效', submission_unknown: '待核实提交',
}
export function StatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`status-badge ${status}`}>{statusLabels[status]}</span>
}
export function ErrorNotice({ error }: { error: unknown }) {
  return error ? <p className="notice error" role="alert">{error instanceof Error ? error.message : '请求失败，请重试。'}</p> : null
}
export function Loading() {
  return <p className="loading" role="status"><Loader2 size={18} className="spin" />加载中…</p>
}
export function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}
export function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`
  return `${(value / 1024 ** 3).toFixed(1)} GB`
}
