import { useEffect, useState } from 'react'
import { api, setToken, type AuthUser } from './api'
import Home from './pages/Home'
import JobPage from './pages/JobPage'
import Login from './pages/Login'
import UsersPage from './pages/UsersPage'

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash.replace(/^#/, '') || '/'
}

export default function App() {
  const route = useHashRoute()
  const [gee, setGee] = useState<boolean | null>(null)
  const [auth, setAuth] = useState<{ enabled: boolean; user: AuthUser | null } | null>(null)

  useEffect(() => {
    api.health().then((h) => setGee(h.gee_project_configured)).catch(() => setGee(false))
    api.authStatus().then(setAuth).catch(() => setAuth({ enabled: false, user: null }))
    const onSignedOut = () => setAuth({ enabled: true, user: null })
    window.addEventListener('pikdrishti-signed-out', onSignedOut)
    return () => window.removeEventListener('pikdrishti-signed-out', onSignedOut)
  }, [])

  const signOut = () => {
    setToken('')
    setAuth({ enabled: true, user: null })
    window.location.hash = '#/'
  }

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [route])

  const jobMatch = route.match(/^\/jobs\/([a-z0-9]{12})$/)
  const signedOut = !!auth?.enabled && !auth.user
  const user = auth?.user ?? null

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#/">
            <img src="/favicon.svg" width={38} height={38} alt="" />
            <span className="wordmark">Pik-drishti <em>AI</em></span>
          </a>
          <nav className="nav">
            {!signedOut && <a href="#/" onClick={(e) => {
              e.preventDefault()
              if (route !== '/') window.location.hash = '#/'
              setTimeout(() => document.getElementById('assessments')?.scrollIntoView({ behavior: 'smooth' }), 50)
            }}>Assessments</a>}
            {user && <a href="#/users">{user.role === 'admin' ? 'Users' : 'Account'}</a>}
            <span className={`conn ${gee === null ? '' : gee ? 'ok' : 'bad'}`}
              title={gee ? 'Earth Engine connected' : 'Earth Engine not configured'}>
              <i />{gee === null ? '…' : gee ? 'Online' : 'Offline'}
            </span>
            {user && <button className="btn btn-quiet" onClick={signOut} title={`Signed in as ${user.username}`}>Sign out</button>}
          </nav>
        </div>
      </header>
      {auth === null ? (
        <main className="page" />
      ) : signedOut ? (
        <Login onSignedIn={(u) => setAuth({ enabled: true, user: u })} />
      ) : route === '/users' && user ? (
        <UsersPage me={user} />
      ) : jobMatch ? (
        <JobPage key={jobMatch[1]} jobId={jobMatch[1]} />
      ) : (
        <Home />
      )}
      <footer className="footer">
        <div className="footer-inner">Pik-drishti AI · IIIT Nagpur · Satellite data: NASA, ESA / Copernicus, UCSB CHC</div>
      </footer>
    </div>
  )
}
