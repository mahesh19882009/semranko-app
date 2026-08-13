'use client'
import { useState } from 'react';
import { Link, useSearchParams } from '../lib/navigation';
import { normalizeApiError, resendMobileOtpApi, verifyMobileOtpApi } from '../lib/api';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import TurnstileWidget from '../components/TurnstileWidget';

export default function VerifyMobilePage() {
  const [searchParams] = useSearchParams();
  const fromLogin = searchParams.get('source') === 'login';
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [verified, setVerified] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState(null);
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('mobileVerificationToken') : null;

  const verify = async (event) => {
    event.preventDefault();
    if (!token || loading) return;
    setLoading(true); setError(''); setMessage('');
    try {
      await verifyMobileOtpApi(token, otp);
      sessionStorage.removeItem('mobileVerificationToken');
      setVerified(true);
      setMessage(fromLogin ? 'Mobile number verified. You can now log in.' : 'Mobile number verified. Please also use the link sent to your email before logging in.');
    } catch (err) {
      setError(normalizeApiError(err, 'Mobile verification failed.').message);
    } finally { setLoading(false); }
  };

  const resend = async () => {
    if (!token || loading) return;
    setLoading(true); setError(''); setMessage('');
    try {
      await resendMobileOtpApi(token, turnstileToken);
      setMessage('A new OTP was sent.');
    } catch (err) { setError(normalizeApiError(err, 'Could not resend OTP.').message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Verify mobile number</h1>
        <p className="mt-2 text-sm text-slate-600">Enter the six-digit OTP sent to your registered mobile number. Email verification is also required.</p>
        {!token && !verified && <div className="mt-4"><Alert variant="error" message="Your mobile verification session is missing or expired. Please log in again." /></div>}
        {error && <div className="mt-4"><Alert variant="error" message={error} /></div>}
        {message && <div className="mt-4"><Alert variant="success" message={message} /></div>}
        {!verified && token && (
          <form onSubmit={verify} className="mt-5 space-y-4">
            <input value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" placeholder="6-digit OTP" className="w-full rounded-xl border border-slate-300 px-4 py-3" required />
            <Button type="submit" loading={loading} disabled={otp.length !== 6 || loading} fullWidth>Verify mobile</Button>
            <TurnstileWidget action="otp_send" onToken={setTurnstileToken} />
            <button type="button" onClick={resend} disabled={loading} className="w-full text-sm font-medium text-indigo-600 disabled:opacity-50">Send / resend OTP</button>
          </form>
        )}
        <Link to={verified ? (fromLogin ? '/login' : '/login?emailVerificationPending=true') : (fromLogin ? '/login' : '/register')} className="mt-5 inline-block text-sm font-medium text-slate-700 underline">{verified ? 'Continue to login' : (fromLogin ? 'Back to login' : 'Back to registration')}</Link>
      </div>
    </div>
  );
}
