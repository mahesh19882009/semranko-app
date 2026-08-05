'use client'
import { Provider } from 'react-redux'
import { HelmetProvider } from 'react-helmet-async'
import { store } from '@/src/app/store'
import { ToastProvider } from '@/src/components/ui/Toast'

export function Providers({ children }) {
  return (
    <Provider store={store}>
      <HelmetProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </HelmetProvider>
    </Provider>
  )
}
