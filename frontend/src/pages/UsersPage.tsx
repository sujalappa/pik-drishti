import { useEffect, useState, type FormEvent } from 'react'
import { api, type AuthUser, type UserRow } from '../api'

const message = (err: unknown) => (err instanceof Error ? err.message : 'Something went wrong')

function AddUser({ onAdded }: { onAdded: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.addUser(username.trim(), password, role)
      setUsername('')
      setPassword('')
      setRole('user')
      onAdded()
    } catch (err) {
      setError(message(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <div className="panel-head"><h2>Add a user</h2></div>
      <div className="panel-body">
        <div className="form-row" style={{ marginTop: 0 }}>
          <label htmlFor="new-user">User ID</label>
          <input id="new-user" type="text" autoComplete="off" required minLength={3} maxLength={32} value={username}
            onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="new-pass">Password (at least 8 characters)</label>
          <input id="new-pass" type="password" autoComplete="new-password" required minLength={8} value={password}
            onChange={(e) => setPassword(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="new-role">Role</label>
          <select id="new-role" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="user">User: can run and view assessments</option>
            <option value="admin">Admin: can also manage users</option>
          </select>
        </div>
        {error && <div className="error-box">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Adding…' : 'Add user'}</button>
      </div>
    </form>
  )
}

function ChangePassword() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await api.changePassword(current, next)
      setCurrent('')
      setNext('')
      setNote({ ok: true, text: 'Password changed.' })
    } catch (err) {
      setNote({ ok: false, text: message(err) })
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <div className="panel-head"><h2>Change my password</h2></div>
      <div className="panel-body">
        <div className="form-row" style={{ marginTop: 0 }}>
          <label htmlFor="pw-current">Current password</label>
          <input id="pw-current" type="password" autoComplete="current-password" required value={current}
            onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div className="form-row">
          <label htmlFor="pw-new">New password (at least 8 characters)</label>
          <input id="pw-new" type="password" autoComplete="new-password" required minLength={8} value={next}
            onChange={(e) => setNext(e.target.value)} />
        </div>
        {note && <div className={note.ok ? 'ok-box' : 'error-box'}>{note.text}</div>}
        <button className="btn btn-block">Change password</button>
      </div>
    </form>
  )
}

export default function UsersPage({ me }: { me: AuthUser }) {
  const [users, setUsers] = useState<UserRow[]>([])
  const [error, setError] = useState('')
  const admin = me.role === 'admin'

  const load = () => {
    if (admin) api.users().then(setUsers).catch((err) => setError(message(err)))
  }
  useEffect(load, [admin])

  const remove = async (username: string) => {
    if (!window.confirm(`Remove ${username}? They will be signed out at once.`)) return
    setError('')
    try {
      await api.removeUser(username)
    } catch (err) {
      setError(message(err))
    }
    load()
  }

  const self = users.find((u) => u.username === me.username)
  return (
    <main className="page users-page">
      <div className="section-head"><h2>{admin ? 'Users' : 'Account'}</h2></div>
      <div className="users-grid">
        {admin && (
          <div className="panel">
            <table className="data-table">
              <thead><tr><th>User ID</th><th>Role</th><th>Added</th><th /></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.username}>
                    <td><strong>{u.username}</strong>{u.username === me.username && <span className="muted"> (you)</span>}</td>
                    <td>{u.role === 'admin' ? 'Admin' : 'User'}</td>
                    <td className="muted">{u.builtin ? 'Built-in' : u.created_at?.slice(0, 10)}</td>
                    <td className="num">
                      {!u.builtin && u.username !== me.username && (
                        <button className="btn btn-quiet" onClick={() => remove(u.username)}>Remove</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {error && <div className="panel-body"><div className="error-box" style={{ marginTop: 0 }}>{error}</div></div>}
          </div>
        )}
        <div className="users-side">
          {admin && <AddUser onAdded={load} />}
          {!(admin && (!self || self.builtin)) && <ChangePassword />}
        </div>
      </div>
    </main>
  )
}
