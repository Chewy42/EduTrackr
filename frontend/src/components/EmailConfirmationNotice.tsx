import { useState } from 'react'
import AuthCard from './AuthCard'
import SubmitButton from './SubmitButton'

interface Props {
  email: string
  onResend: () => Promise<void>
  onBack: () => void
}

export default function EmailConfirmationNotice({ email, onResend, onBack }: Props) {
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const handleResend = async () => {
    setStatus('sending')
    setError(null)
    try {
      await onResend()
      setStatus('sent')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to resend email.'
      setError(message)
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted text-text-primary px-4">
      <AuthCard
        title="Confirm your email"
        subtitle="We sent you a link. Activate your account to continue."
      >
        <div className="text-[0.95rem] text-text-secondary mb-4">
          Check{' '}
          <span className="font-semibold text-text-primary">{email}</span> and click the
          {' '}confirmation button in that email. Once confirmed, return here to sign in.
        </div>
        {error ? (
          <div className="text-sm text-danger mb-2 text-center">
            {error}
          </div>
        ) : null}
        <div className="space-y-2 pt-1">
          <SubmitButton loading={status === 'sending'} onClick={handleResend}>
            {status === 'sent' ? 'Email sent' : 'Resend confirmation email'}
          </SubmitButton>
          <button
            type="button"
            onClick={onBack}
            className="w-full text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors pt-1"
          >
            Back to sign in
          </button>
        </div>
      </AuthCard>
    </div>
  )
}
