import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { getAccessToken, setAccessToken, setStoredUser } from "../utils/auth";
import { apiRequest } from "../lib/api";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const from = location.state?.from?.pathname || "/app";
  const emailVerificationPending = searchParams.get("emailVerificationPending") === "true";
  const selectedPlan = searchParams.get("plan");
  
  const [form, setForm] = useState({
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (getAccessToken()) {
      navigate(from, { replace: true });
    }
  }, [navigate, from]);

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify(form),
      });

      setAccessToken(data.data.accessToken);
      setStoredUser(data.data.user);

      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Login</h1>
        <p style={styles.subtitle}>Access your RankCare dashboard</p>

        {emailVerificationPending && (
          <div style={styles.warningBox}>
            Please verify your email before logging in.{" "}
            <Link to="/resend-verification" style={styles.warningLink}>
              Resend email
            </Link>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            type="email"
            name="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
          />
          <input
            style={styles.input}
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
          />
          <div style={styles.forgotPasswordContainer}>
            <Link to="/forgot-password" style={styles.forgotPasswordLink}>
              Forgot password?
            </Link>
          </div>

          {error && <Alert variant="error" message={error} />}
          {error === "Please verify your email before logging in" ? (
            <p style={styles.helperText}>
              Need a new link? <Link to="/resend-verification">Resend verification email</Link>
            </p>
          ) : null}

          <Button type="submit" disabled={loading} loading={loading} fullWidth>
            Login
          </Button>
        </form>

        <p style={styles.footerText}>
          Don&apos;t have an account?{" "}
          <Link to={selectedPlan ? `/register?plan=${selectedPlan}` : "/register"}>
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}

const styles = {
  helperText: {
    margin: 0,
    fontSize: "14px",
    color: "#667085",
  },
  wrapper: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    background: "#f5f7fb",
    padding: "24px",
  },
  card: {
    width: "100%",
    maxWidth: "420px",
    background: "#fff",
    padding: "32px",
    borderRadius: "16px",
    boxShadow: "0 10px 30px rgba(0,0,0,0.08)",
  },
  title: {
    margin: 0,
    fontSize: "28px",
    fontWeight: 700,
  },
  subtitle: {
    margin: "8px 0 24px",
    color: "#667085",
  },
  warningBox: {
    marginBottom: "16px",
    padding: "12px 14px",
    borderRadius: "10px",
    border: "1px solid #f5c16c",
    background: "#fff7e6",
    color: "#9a6700",
    fontSize: "14px",
    lineHeight: 1.5,
  },
  warningLink: {
    color: "#9a6700",
    fontWeight: 600,
    textDecoration: "underline",
  },
  form: {
    display: "grid",
    gap: "14px",
  },
  input: {
    width: "100%",
    padding: "14px 16px",
    borderRadius: "10px",
    border: "1px solid #d0d5dd",
    fontSize: "15px",
  },
  button: {
    border: "none",
    padding: "14px 16px",
    borderRadius: "10px",
    background: "#111827",
    color: "#fff",
    fontSize: "15px",
    cursor: "pointer",
  },
  error: {
    color: "#d92d20",
    margin: 0,
    fontSize: "14px",
  },
  footerText: {
    marginTop: "18px",
    fontSize: "14px",
    color: "#667085",
  },
  forgotPasswordContainer: {
    textAlign: "right",
  },
  forgotPasswordLink: {
    fontSize: "14px",
    color: "#667085",
    textDecoration: "none",
  },
};

export default LoginPage;