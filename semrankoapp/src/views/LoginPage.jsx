'use client'
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "../lib/navigation";
import { clearStoredUser, setStoredUser } from "../utils/auth";
import { apiRequest, createMobileVerificationSessionApi, normalizeApiError } from "../lib/api";
import TurnstileWidget from '../components/TurnstileWidget';

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const requestedReturnTo = searchParams.get('returnTo');
  const safeReturnTo = requestedReturnTo?.startsWith('/') && !requestedReturnTo.startsWith('//')
    ? requestedReturnTo
    : null;
  const from = location.state?.from?.pathname || safeReturnTo || "/dashboard";
  const emailVerificationPending = searchParams.get("emailVerificationPending") === "true";
  const sessionExpired = searchParams.get("sessionExpired") === "true";
  const selectedPlan = searchParams.get("plan");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [accountIssue, setAccountIssue] = useState(null);
  const [turnstileToken, setTurnstileToken] = useState(null);
  const [challengeRequired, setChallengeRequired] = useState(false);

  useEffect(() => {
    let active = true;
    apiRequest('/auth/me')
      .then(() => { if (active) navigate(from, { replace: true }); })
      .catch(() => { if (active) clearStoredUser(); });
    return () => { active = false; };
  }, [navigate, from]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setError("");
    setAccountIssue(null);
    setLoading(true);

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, turnstileToken }),
      });

      setStoredUser(data.data.user);

      navigate(from, { replace: true });
    } catch (err) {
      const normalized = normalizeApiError(err, 'Login failed. Please try again.');
      if (normalized.code === 'MOBILE_VERIFICATION_REQUIRED') {
        setAccountIssue({ type: 'mobile', message: normalized.message });
      } else if (normalized.code === 'EMAIL_VERIFICATION_REQUIRED') {
        setAccountIssue({ type: 'email', message: normalized.message });
      } else {
        if (normalized.code === 'TURNSTILE_REQUIRED' || normalized.code === 'TURNSTILE_REJECTED') setChallengeRequired(true);
        setError(normalized.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const continueMobileVerification = async () => {
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      const session = await createMobileVerificationSessionApi(email, password);
      const verificationToken = session?.data?.mobileVerificationToken;
      if (!verificationToken) throw new Error('Mobile verification is already complete. Please log in again.');
      sessionStorage.setItem('mobileVerificationToken', verificationToken);
      if (session?.data?.mobileMasked) sessionStorage.setItem('mobileVerificationMasked', session.data.mobileMasked);
      navigate('/verify-mobile?source=login');
    } catch (err) {
      setError(normalizeApiError(err, 'Could not start mobile verification.').message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "calc(100vh - 135px)",
      display: "grid",
      placeItems: "center",
      background: "#f5f7fb",
      padding: "24px"
    }}>
      <div style={{
        width: "100%",
        maxWidth: "420px",
        background: "#fff",
        padding: "32px",
        borderRadius: "16px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.08)"
      }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 700 }}>Login</h1>
        <p style={{ margin: "8px 0 24px", color: "#667085" }}>Access your Semranko dashboard</p>

        {emailVerificationPending && (
          <div style={{
            marginBottom: "16px",
            padding: "12px 14px",
            borderRadius: "10px",
            border: "1px solid #f5c16c",
            background: "#fff7e6",
            color: "#9a6700",
            fontSize: "14px"
          }}>
            Please verify your email before logging in.{" "}
            <Link to="/resend-verification" style={{ color: "#9a6700", fontWeight: 600, textDecoration: "underline" }}>
              Resend email
            </Link>
          </div>
        )}

        {sessionExpired && !emailVerificationPending && (
          <div style={{ marginBottom: "16px", padding: "12px 14px", borderRadius: "10px", border: "1px solid #f5c16c", background: "#fff7e6", color: "#9a6700", fontSize: "14px" }}>
            Your session expired. Please log in again.
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "grid", gap: "14px" }}>
          <input
            style={{
              width: "100%",
              padding: "14px 16px",
              borderRadius: "10px",
              border: "1px solid #d0d5dd",
              fontSize: "15px"
            }}
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <div style={{ position: "relative" }}>
            <input
              style={{
                width: "100%",
                padding: "14px 48px 14px 16px",
                borderRadius: "10px",
                border: "1px solid #d0d5dd",
                fontSize: "15px"
              }}
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(prev => !prev)}
              style={{
                position: "absolute",
                right: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: "18px",
                padding: "4px",
                lineHeight: 1
              }}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "🙈" : "👁️"}
            </button>
          </div>
          <div style={{ textAlign: "right" }}>
            <Link to="/forgot-password" style={{ fontSize: "14px", color: "#667085", textDecoration: "none" }}>
              Forgot password?
            </Link>
          </div>

          {accountIssue && (
            <div style={{ padding: "14px", borderRadius: "10px", background: "#fff7e6", color: "#7c4a03", fontSize: "14px", border: "1px solid #f5c16c" }}>
              <strong style={{ display: 'block', marginBottom: '4px' }}>
                {accountIssue.type === 'mobile' ? 'Mobile verification required' : 'Email verification required'}
              </strong>
              <span>{accountIssue.message}</span>
              {accountIssue.type === 'mobile' ? (
                <button type="button" disabled={loading} onClick={continueMobileVerification} style={{ display: 'block', marginTop: '10px', border: 0, background: 'transparent', padding: 0, color: '#7c3aed', fontWeight: 700, cursor: 'pointer' }}>
                  Verify mobile number
                </button>
              ) : (
                <Link to={`/resend-verification?email=${encodeURIComponent(email)}`} style={{ display: 'block', marginTop: '10px', color: '#7c3aed', fontWeight: 700 }}>
                  Resend verification email
                </Link>
              )}
            </div>
          )}

          {error && (
            <div style={{
              padding: "10px 14px",
              borderRadius: "10px",
              background: "#fef2f2",
              color: "#b91c1c",
              fontSize: "14px",
              border: "1px solid #fecaca"
            }}>
              {error}
            </div>
          )}

          {challengeRequired && <TurnstileWidget action="login" onToken={setTurnstileToken} />}

          <button
            type="submit"
            disabled={loading}
            style={{
              border: "none",
              padding: "14px 16px",
              borderRadius: "10px",
              background: "#111827",
              color: "#fff",
              fontSize: "15px",
              opacity: loading ? 0.6 : 1,
              cursor: loading ? "not-allowed" : "pointer"
            }}
          >
            {loading ? "Logging in..." : "Click to login"}
          </button>

          <p style={{
            marginTop: "18px",
            fontSize: "14px",
            color: "#667085",
            textAlign: "center"
          }}>
            Don&apos;t have an account?{" "}
            <Link to={selectedPlan ? `/register?plan=${selectedPlan}` : "/register"} style={{ color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
              Register
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
