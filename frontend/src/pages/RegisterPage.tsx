import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../lib/api'
import { useAuth } from '../lib/auth'

export function RegisterPage() {
  const { signUp } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    const form = new FormData(event.currentTarget)
    try {
      await signUp({
        name: String(form.get('name')),
        email: String(form.get('email')),
        password: String(form.get('password')),
      })
      navigate('/dashboard')
    } catch (err) {
      setError(getApiErrorMessage(err, 'Registration failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-12">
      <form className="panel w-full space-y-5" onSubmit={handleSubmit}>
        <div>
          <h1 className="text-3xl font-black text-white">Create account</h1>
          <p className="mt-2 text-sm text-slate-400">Set up your profile to file reports and track matches.</p>
        </div>
        <Field label="Name" name="name" type="text" />
        <Field label="Email" name="email" type="email" />
        <Field label="Password" name="password" type="password" />
        {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div> : null}
        <button className="btn-primary w-full" disabled={loading} type="submit">
          {loading ? 'Creating…' : 'Create account'}
        </button>
        <p className="text-center text-sm text-slate-400">
          Already have an account? <Link to="/login" className="text-emerald-300 hover:text-emerald-200">Sign in</Link>
        </p>
      </form>
    </main>
  )
}

function Field({ label, name, type }: { label: string; name: string; type: string }) {
  return (
    <div>
      <label className="label" htmlFor={name}>{label}</label>
      <input id={name} name={name} type={type} required className="input" />
    </div>
  )
}
