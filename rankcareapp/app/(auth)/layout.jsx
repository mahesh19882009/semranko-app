'use client'
import { useEffect, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import AppLayout from '@/src/components/AppLayout'
import { clearStoredUser, setStoredUser } from '@/src/utils/auth'
import { apiRequest } from '@/src/lib/api'

export default function AppLayoutWrapper({ children, params }) {
  use(params)

  const router = useRouter()
  const [authenticated, setAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    let active = true
    apiRequest('/auth/me')
      .then((result) => {
        if (!active) return
        const currentUser = result?.data || null
        setStoredUser(currentUser)
        setUser(currentUser)
        setAuthenticated(true)
      })
      .catch(() => {
        if (!active) return
        clearStoredUser()
        setAuthenticated(false)
      })
      .finally(() => { if (active) setAuthChecked(true) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!authChecked) return
    if (!authenticated) {
      const returnTo = `${window.location.pathname}${window.location.search}`
      router.replace(`/login?returnTo=${encodeURIComponent(returnTo)}`)
      return
    }
    if (user && user.isVerified === false) {
      router.replace('/verify-email')
    }
  }, [authChecked, authenticated, user, router])

  if (!authChecked || !authenticated) {
    return null
  }

  return <AppLayout>{children}</AppLayout>
}
