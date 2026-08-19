'use client'

import { useEffect } from 'react'

export default function AppError({ error, reset }) {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production') console.error('Unexpected route error:', error)
  }, [error])

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <section className="w-full max-w-md rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Something went wrong</h1>
        <p className="mt-2 text-sm text-slate-600">We couldn&apos;t display this page. Your data is safe; please try again.</p>
        <div className="mt-6 flex justify-center gap-3">
          <button type="button" onClick={reset} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Try Again</button>
          <a href="/dashboard" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Return to Dashboard</a>
        </div>
      </section>
    </main>
  )
}
