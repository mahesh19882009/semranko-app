import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { registerApi } from "../lib/api";
import { PLANS, TRIAL_DAYS, VALID_PLAN_KEYS } from "../config/pricing";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const initialPlanFromUrl = searchParams.get("plan")?.toLowerCase() || "starter";
  const safeInitialPlan = VALID_PLAN_KEYS.includes(initialPlanFromUrl) ? initialPlanFromUrl : "starter";

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    selectedPlan: safeInitialPlan,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedPlanMeta =
    PLANS.find((plan) => plan.key === form.selectedPlan) || PLANS[0];

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePlanSelect = (planKey) => {
    setForm((prev) => ({
      ...prev,
      selectedPlan: planKey,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      await registerApi({
        name: form.name,
        email: form.email,
        password: form.password,
        selectedPlan: form.selectedPlan,
      });

      setSuccess("Registration successful. Please verify your email before logging in.");
      setTimeout(() => {
        navigate(`/login?emailVerificationPending=true&plan=${form.selectedPlan}`);
      }, 700);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Register</h1>
        <p style={styles.subtitle}>Create your RankCare account and start your {TRIAL_DAYS}-day trial</p>

        <div style={styles.planBox}>
          <p style={styles.planBoxLabel}>Selected plan</p>

          <div style={styles.planList}>
            {PLANS.map((plan) => {
              const active = form.selectedPlan === plan.key;

              return (
                <Button
                  key={plan.key}
                  type="button"
                  variant={active ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => handlePlanSelect(plan.key)}
                  style={styles.planChip}
                >
                  {plan.name}
                </Button>
              );
            })}
          </div>

          <div style={styles.planSummary}>
            <p style={styles.planSummaryTitle}>
              {selectedPlanMeta.name} plan selected
            </p>
            <p style={styles.planSummaryText}>
              Trial: {TRIAL_DAYS} days, then continue with the {selectedPlanMeta.name} plan when billing is enabled.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            type="text"
            name="name"
            placeholder="Full name"
            value={form.name}
            onChange={handleChange}
          />

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

          <input type="hidden" name="selectedPlan" value={form.selectedPlan} readOnly />

          {error && <Alert variant="error" message={error} />}
          {success && <Alert variant="success" message={success} />}

          <Button type="submit" disabled={loading} loading={loading} fullWidth>
            Start trial
          </Button>
        </form>

        <p style={styles.footerText}>
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    background: "#f5f7fb",
    padding: "24px",
  },
  card: {
    width: "100%",
    maxWidth: "460px",
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
    lineHeight: 1.6,
  },
  planBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "14px",
    padding: "16px",
    marginBottom: "20px",
  },
  planBoxLabel: {
    margin: "0 0 12px",
    fontSize: "13px",
    fontWeight: 700,
    color: "#475467",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  planList: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    marginBottom: "14px",
  },
  planChip: {
    border: "1px solid #d0d5dd",
    background: "#ffffff",
    color: "#344054",
    padding: "10px 14px",
    borderRadius: "999px",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
  },
  planChipActive: {
    background: "#2563eb",
    color: "#ffffff",
    border: "1px solid #2563eb",
  },
  planSummary: {
    background: "#ffffff",
    border: "1px solid #dbeafe",
    borderRadius: "12px",
    padding: "14px",
  },
  planSummaryTitle: {
    margin: "0 0 6px",
    fontSize: "15px",
    fontWeight: 700,
    color: "#0f172a",
  },
  planSummaryText: {
    margin: 0,
    color: "#475467",
    fontSize: "14px",
    lineHeight: 1.6,
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
    fontWeight: 700,
  },
  error: {
    color: "#d92d20",
    margin: 0,
    fontSize: "14px",
  },
  success: {
    color: "#067647",
    margin: 0,
    fontSize: "14px",
  },
  footerText: {
    marginTop: "18px",
    fontSize: "14px",
    color: "#667085",
  },
};

export default RegisterPage;