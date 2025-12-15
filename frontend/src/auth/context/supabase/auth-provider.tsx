import { useEffect, useCallback, useMemo, useState } from 'react'
import { supabase } from '../../../services/supabase'
import { AuthContext } from '../auth-context'
import type { AuthState, UserType } from '../../types'

type Props = {
  children: React.ReactNode
}

export function AuthProvider({ children }: Props) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true })

  const checkUserSession = useCallback(async () => {
    try {
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error getting session:', error)
        setState({ user: null, loading: false })
        return
      }

      if (session?.user) {
        setState({ user: session.user as UserType, loading: false })
      } else {
        setState({ user: null, loading: false })
      }
    } catch (error) {
      console.error('Error checking user session:', error)
      setState({ user: null, loading: false })
    }
  }, [])

  useEffect(() => {
    // Check initial session
    checkUserSession()

    // Listen to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setState({ user: session.user as UserType, loading: false })
      } else {
        setState({ user: null, loading: false })
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [checkUserSession])

  const checkAuthenticated = state.user ? 'authenticated' : 'unauthenticated'
  const status = state.loading ? 'loading' : checkAuthenticated

  const memoizedValue = useMemo(
    () => ({
      user: state.user,
      checkUserSession,
      loading: status === 'loading',
      authenticated: status === 'authenticated',
      unauthenticated: status === 'unauthenticated',
    }),
    [checkUserSession, state.user, status]
  )

  return <AuthContext.Provider value={memoizedValue}>{children}</AuthContext.Provider>
}
