import { useEffect } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { List, Plus, Settings, Users } from 'lucide-react'
import { api } from './lib/api'
import QueuePage from './pages/QueuePage'
import RequestPage from './pages/RequestPage'
import AccountsPage from './pages/AccountsPage'
import SettingsPage from './pages/SettingsPage'
import brandMark from './assets/brand-mark.png'

const navigation = [
  { to: '/tasks', label: '请求队列', icon: List },
  { to: '/requests/new', label: '提交请求', icon: Plus },
  { to: '/accounts', label: '账号', icon: Users },
  { to: '/settings', label: '设置', icon: Settings },
]
export default function App() {
  const queryClient = useQueryClient()
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary, refetchInterval: 5000 })
  useEffect(() => {
    const source = new EventSource('/api/v1/events')
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    }
    const events = ['task.created', 'task.status_changed', 'task.query_retry', 'task.resubmitted', 'task.recovered', 'task.deleted']
    events.forEach((event) => source.addEventListener(event, refresh))
    return () => source.close()
  }, [queryClient])
  return <div className="app-shell">
    <header className="app-header">
      <NavLink to="/tasks" className="brand"><img src={brandMark} alt="" /><strong>ECMWF Downloader</strong></NavLink>
      <nav aria-label="主导航">{navigation.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><Icon size={17} />{label}</NavLink>)}</nav>
      <span className={`connection ${summary.isError ? 'offline' : ''}`} role="status">{summary.isError ? '服务连接失败' : !summary.data ? '正在连接' : '服务已连接'}</span>
    </header>
    <main><Routes>
      <Route path="/tasks" element={<QueuePage />} />
      <Route path="/requests/new" element={<RequestPage />} />
      <Route path="/accounts" element={<AccountsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/tasks" replace />} />
    </Routes></main>
  </div>
}
