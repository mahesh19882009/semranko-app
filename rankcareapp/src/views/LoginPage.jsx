'use client'
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "../lib/navigation";
import { getAccessToken, setAccessToken, setStoredUser, setSessionToken } from "../utils/auth";
import { apiRequest } from "../lib/api";

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const from = location.state?.from?.pathname || "/dashboard";
  const emailVerificationPending = searchParams.get("emailVerificationPending") === "true";
  const selectedPlan = searchParams.get("plan");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [clickCount, setClickCount] = useState(0);

  useEffect(() => {
    if (getAccessToken()) {
      navigate(from, { replace: true });
    }
  }, [navigate, from]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setClickCount(c => c + 1);
    console.log('LOGIN CLICKED', { email, password, clickCount: clickCount + 1 });
    setError("");
    setLoading(true);

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      setAccessToken(data.data.accessToken);
      setStoredUser(data.data.user);
      setSessionToken(data.data.sessionToken);

      navigate(from, { replace: true });
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || "Something went wrong");
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
        <p style={{ margin: "8px 0 24px", color: "#667085" }}>Access your RankCare dashboard</p>

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
