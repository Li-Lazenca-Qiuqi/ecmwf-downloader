import { Loader2 } from 'lucide-react'
import { type TaskStatus } from './lib/api'

export const statusLabels: Record<TaskStatus, string> = {
  pending: '历史未入队', queued: '排队中', running: '下载中', completed: '已完成',
  failed: '失败', retry_wait: '等待重试', cancelling: '取消中', cancelled: '已取消',
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
