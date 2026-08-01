'use client'
import { Provider } from 'react-redux'
import { HelmetProvider } from 'react-helmet-async'
import { store } from '@/src/app/store'

export function Providers({ children }) {
  return (
    <Provider store={store}>
      <HelmetProvider>
        {children}
      </HelmetProvider>
    </Provider>
  )
}
