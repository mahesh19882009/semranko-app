'use client'

import NextLink from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState, useMemo, useCallback } from 'react'

export function Link({ to, href, children, style, className, ...props }) {
  const path = to || href
  return (
    <NextLink href={path} className={className} {...props}>
      {children}
    </NextLink>
  )
}

export function useNavigate() {
  const router = useRouter()

  return useCallback((to, options) => {
    if (options && options.replace) {
      router.replace(to)
    } else {
      router.push(to)
    }
  }, [router])
}

export function useLocation() {
  const pathname = usePathname()
  const [search, setSearch] = useState('')

  useEffect(() => {
    setSearch(window.location.search)
  }, [pathname])

  return {
    pathname,
    search,
    hash: '',
    state: null,
    key: '',
  }
}

export function useSearchParams() {
  const [search, setSearch] = useState('')

  const pathname = usePathname()

  useEffect(() => {
    setSearch(window.location.search)
  }, [pathname])

  const params = useMemo(() => new URLSearchParams(search), [search])
  const router = useRouter()

  const setSearchParams = useCallback((newParams, options) => {
    const url = new URL(window.location.href)
    url.search = ''

    if (newParams instanceof URLSearchParams) {
      newParams.forEach((v, k) => url.searchParams.set(k, v))
    } else if (typeof newParams === 'object' && newParams !== null) {
      Object.entries(newParams).forEach(([k, v]) =>
        url.searchParams.set(k, String(v))
      )
    }

    const fullPath = `${window.location.pathname}${url.search}`

    if (options && options.replace) {
      router.replace(fullPath)
    } else {
      router.push(fullPath)
    }
  }, [router])

  return [params, setSearchParams]
}

export function Navigate({ to, replace, state, ...props }) {
  const router = useRouter()
  useEffect(() => {
    if (replace) {
      router.replace(to)
    } else {
      router.push(to)
    }
  }, [to, replace, state, router])
  return null
}

export function NavLink({ to, href, className, activeClassName, end, ...props }) {
  const pathname = usePathname()
  const path = to || href
  const isActive = end ? pathname === path : pathname.startsWith(path)
  const cls = `${className || ''} ${isActive ? activeClassName || 'active' : ''}`.trim()

  return <NextLink href={path} className={cls} {...props}></NextLink>
}

export function Outlet({ children }) {
  return children
}
