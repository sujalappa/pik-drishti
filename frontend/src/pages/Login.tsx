import { useState, type FormEvent } from 'react'
import { api, setToken, type AuthUser } from '../api'

const REQUEST_BODY = [
  'Hi Sujal,',
  '',
  'I would like access to the Pik-drishti AI demo. Please share a user ID and password.',
  '',
  'Name:',
  'Organisation:',
  '',
  'Thank you',
].join('\n')
const REQUEST_ACCESS = 'mailto:sujalchondhekar@gmail.com'
  + `?subject=${encodeURIComponent('Access request: Pik-drishti AI demo')}&body=${encodeURIComponent(REQUEST_BODY)}`

export default function Login({ onSignedIn }: { onSignedIn: (user: AuthUser) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await api.login(username.trim(), password)
      setToken(res.token)
      onSignedIn(res.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-wrap">
      <form className="panel login-card" onSubmit={submit}>
        <h1>Sign in</h1>
        <div className="form-row">
          <label htmlFor="login-user">User ID</label>
          <input id="login-user" type="text" autoComplete="username" autoFocus required value={username}
            onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="login-pass">Password</label>
          <input id="login-pass" type="password" autoComplete="current-password" required value={password}
            onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <div className="error-box">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="login-request small muted">
          No account? <a href={REQUEST_ACCESS} target="_top">Request access</a>
        </p>
      </form>
    </main>
  )
}
