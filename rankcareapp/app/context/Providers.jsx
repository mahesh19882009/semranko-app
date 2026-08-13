'use client'
import { useEffect } from 'react'
import { Provider } from 'react-redux'
import { HelmetProvider } from 'react-helmet-async'
import { store } from '@/src/app/store'
import { ToastProvider } from '@/src/components/ui/Toast'
import ErrorBoundary from '@/src/components/ErrorBoundary'
import { clearLegacyCredentials } from '@/src/utils/auth'

export function Providers({ children }) {
  useEffect(() => { clearLegacyCredentials() }, [])
  return (
    <Provider store={store}>
      <HelmetProvider>
        <ToastProvider>
          <ErrorBoundary>{children}</ErrorBoundary>
        </ToastProvider>
      </HelmetProvider>
    </Provider>
  )
}
