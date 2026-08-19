'use client'
import { useState } from 'react';
import { useNavigate, useSearchParams } from '../lib/navigation';
import { resendVerificationApi } from '../lib/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Alert from '../components/ui/Alert';

export default function ResendVerificationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(() => searchParams.get('email') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);

    try {
      await resendVerificationApi(email);
      setSuccess(true);
      setEmail('');
    } catch (err) {
      setError(err.message || 'Failed to resend verification email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Resend Verification Email</h1>
            <p className="text-sm text-slate-600">
              Enter your email address to receive a new verification link.
            </p>
          </div>

          {error && <Alert variant="error" message={error} onDismiss={() => setError('')} />}
          
          {success && (
            <Alert 
              variant="success" 
              message="Verification email sent successfully! Please check your inbox." 
              onDismiss={() => setSuccess(false)} 
            />
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />

            <Button type="submit" disabled={loading} loading={loading} fullWidth>
              {loading ? 'Sending...' : 'Resend Verification Email'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-sm text-slate-600 hover:text-slate-900"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
