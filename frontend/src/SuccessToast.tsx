import { useEffect, useState } from 'react'
import { CircleCheck } from 'lucide-react'

export function useSuccessToast() {
  const [toast, setToast] = useState<{ message: string; duration: number } | null>(null)

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(null), toast.duration)
    return () => window.clearTimeout(timeout)
  }, [toast])

  return {
    message: toast?.message,
    show: (message: string, duration = 3500) => setToast({ message, duration }),
  }
}

export default function SuccessToast({ message }: { message?: string }) {
  return <div className="request-toast" role="status" aria-atomic="true">
    {message && <div className="request-toast-card">
      <CircleCheck size={17} aria-hidden="true" />
      <span>{message}</span>
    </div>}
  </div>
}
