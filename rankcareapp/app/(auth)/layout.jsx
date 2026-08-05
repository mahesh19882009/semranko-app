'use client'
import { useEffect, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import AppLayout from '@/src/components/AppLayout'
import { getStoredUser } from '@/src/utils/auth'

function getIsAuthenticated() {
  if (typeof window === 'undefined') return false
  try {
    return Boolean(window.localStorage.getItem('accessToken'))
  } catch {
    return false
  }
}

export default function AppLayoutWrapper({ children, params }) {
  use(params)

  const router = useRouter()
  const [authenticated, setAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    const isAuth = getIsAuthenticated()
    setAuthenticated(isAuth)
    if (isAuth) {
      setUser(getStoredUser())
    }
    setAuthChecked(true)
  }, [])

  useEffect(() => {
    if (!authChecked) return
    if (!authenticated) {
      router.replace('/login')
      return
    }
    if (user && user.isVerified === false) {
      router.replace('/verify-email')
    }
  }, [authChecked, authenticated, user, router])

  if (!authenticated) {
    return null
  }

  return <AppLayout>{children}</AppLayout>
}
