'use client'
import { useEffect, useState } from "react";
import { Link, useNavigate } from "../lib/navigation";
import { registerApi } from "../lib/api";
import { getAccessToken } from "../utils/auth";

function RegisterPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (getAccessToken()) {
      navigate("/dashboard", { replace: true });
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      await registerApi({
        name,
        email,
        password,
      });

      setSuccess("Registration successful. Please verify your email before logging in.");
      navigate("/login?emailVerificationPending=true");
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "grid",
      placeItems: "center",
      background: "#f5f7fb",
      padding: "24px"
    }}>
      <div style={{
        width: "100%",
        maxWidth: "460px",
        background: "#fff",
        padding: "32px",
        borderRadius: "16px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.08)"
      }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 700 }}>Register</h1>
        <p style={{ margin: "8px 0 24px", color: "#667085", lineHeight: 1.6 }}>
          Create your RankCare account and start your free trial with credits to explore RankCare.
        </p>

        <div style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: "14px",
          padding: "16px",
          marginBottom: "20px"
        }}>
          <p style={{ margin: "0 0 12px", fontSize: "13px", fontWeight: 700, color: "#475467", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Your plan
          </p>

          <div style={{
            background: "#ffffff",
            border: "1px solid #dbeafe",
            borderRadius: "12px",
            padding: "14px"
          }}>
            <p style={{ margin: "0 0 6px", fontSize: "15px", fontWeight: 700, color: "#0f172a" }}>
              7-Day Free Trial
            </p>
            <p style={{ margin: 0, color: "#475467", fontSize: "14px", lineHeight: 1.6 }}>
              You'll get 150 credits to explore all features. After the trial ends, choose a paid plan to continue.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
          <input
            style={{
              width: "100%",
              padding: "14px 16px",
              borderRadius: "10px",
              border: "1px solid #d0d5dd",
              fontSize: "15px"
            }}
            type="text"
            name="name"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="name"
          />

          <input
            style={{
              width: "100%",
              padding: "14px 16px",
              borderRadius: "10px",
              border: "1px solid #d0d5dd",
              fontSize: "15px"
            }}
            type="email"
            name="email"
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
              name="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
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

          {success && (
            <div style={{
              padding: "10px 14px",
              borderRadius: "10px",
              background: "#f0fdf4",
              color: "#047857",
              fontSize: "14px",
              border: "1px solid #bbf7d0"
            }}>
              {success}
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
            {loading ? "Creating account..." : "Start Free Trial"}
          </button>
        </form>

        <p style={{ margin: "24px 0 0", textAlign: "center", color: "#667085", fontSize: "14px" }}>
          Already have an account? <Link to="/login" style={{ color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>Log in</Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
