import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { getApiErrorMessage } from '../lib/api'

export const categories = [
  'Electronics',
  'Documents',
  'Bags',
  'Accessories',
  'Clothing',
  'Keys',
  'Other',
]

type Props = {
  mode: 'lost' | 'found'
  onSubmit: (formData: FormData) => Promise<void>
  submitting: boolean
}

export function ReportForm({ mode, onSubmit, submitting }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    const form = event.currentTarget
    const data = new FormData(form)

    try {
      await onSubmit(data)
      form.reset()
      setPreview(null)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to submit item'))
    }
  }

  return (
    <form className="panel space-y-5" onSubmit={handleSubmit}>
      <div>
        <h1 className="text-2xl font-black text-white">
          {mode === 'lost' ? 'Add Lost Item' : 'Add Found Item'}
        </h1>

        <p className="mt-1 text-sm text-slate-400">
          Enter the item details so the system can search for possible matches.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {mode === 'lost' ? (
          <Field
            label="Item name"
            name="item_name"
            required
          />
        ) : null}

        <Field
          label="Category"
          name="category"
          as="select"
          required
          options={categories}
        />

        <Field
          label="Description"
          name="description"
          as="textarea"
          required
        />

        {mode === 'lost' ? (
          <Field
            label="Date lost"
            name="date_lost"
            type="date"
            required
          />
        ) : (
          <Field
            label="Date found"
            name="date_found"
            type="date"
            required
          />
        )}

        <Field
          label={mode === 'lost' ? 'Location lost' : 'Location found'}
          name="location"
          required
        />
      </div>

      <div>
        <label className="label">Item image</label>

        <input
          className="input"
          type="file"
          name="image"
          accept="image/*"
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            const file = event.target.files?.[0]

            if (!file) {
              setPreview(null)
              return
            }

            setPreview(URL.createObjectURL(file))
          }}
        />

        {preview ? (
          <img
            src={preview}
            alt="Item preview"
            className="mt-4 h-56 w-full rounded-2xl object-cover"
          />
        ) : null}
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <button
        className="btn-primary w-full"
        disabled={submitting}
        type="submit"
      >
        {submitting ? 'Submitting…' : 'Submit Item'}
      </button>
    </form>
  )
}

type FieldProps = {
  label: string
  name: string
  required?: boolean
  as?: 'input' | 'textarea' | 'select'
  type?: string
  options?: string[]
}

function Field({
  label,
  name,
  required,
  as = 'input',
  type = 'text',
  options = [],
}: FieldProps) {
  return (
    <div className={as === 'textarea' ? 'md:col-span-2' : ''}>
      <label className="label" htmlFor={name}>
        {label}
      </label>

      {as === 'textarea' ? (
        <textarea
          id={name}
          name={name}
          required={required}
          rows={5}
          className="input resize-none"
        />
      ) : as === 'select' ? (
        <select
          id={name}
          name={name}
          required={required}
          className="input"
        >
          <option value="">Choose one</option>

          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={name}
          name={name}
          required={required}
          type={type}
          className="input"
        />
      )}
    </div>
  )
}