import { useState } from "react";
import { Link } from "react-router-dom";
import PublicLayout from "../components/PublicLayout";

function ContactPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const contactItems = [
    {
      title: "Sales",
      text: "Talk about plans, agency workflows, and product fit for your team.",
      value: "sales@rankcare.com",
    },
    {
      title: "Support",
      text: "Get help with setup, reports, keyword tracking, and account issues.",
      value: "support@rankcare.com",
    },
    {
      title: "General",
      text: "Reach out for partnerships, feedback, or product questions.",
      value: "hello@rankcare.com",
    },
  ];

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");

    try {
      const response = await fetch("/api/contact/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const result = await response.json();

      if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Failed to send message");
      }

      setMessage(result?.message || "Thank you for your message. We'll get back to you soon.");
      setSubmitted(true);
      setForm({ name: "", email: "", company: "", message: "" });
    } catch (err) {
      setError(err?.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicLayout>
      <section style={styles.heroSection}>
        <div style={styles.container}>
          <div style={styles.heroContent}>
            <span style={styles.badge}>Contact RankCare</span>
            <h1 style={styles.heroTitle}>Talk to us about SEO tracking, reports, and product setup</h1>
            <p style={styles.heroText}>
              Whether you want a demo, pricing clarification, or help understanding how RankCare fits
              your workflow, this page gives users a clean way to reach the team.
            </p>
          </div>
        </div>
      </section>

      <section style={styles.mainSection}>
        <div style={styles.container}>
          <div style={styles.grid}>
            <div style={styles.formCard}>
              <h2 style={styles.sectionTitle}>Send a message</h2>
              <p style={styles.sectionText}>
                Use this basic form now and connect it to your backend or email flow later.
              </p>

              <form style={styles.form} onSubmit={handleSubmit}>
                <div style={styles.fieldGroup}>
                  <label style={styles.label}>Full Name</label>
                  <input
                    type="text"
                    name="name"
                    placeholder="Enter your name"
                    value={form.name}
                    onChange={handleChange}
                    required
                    style={styles.input}
                  />
                </div>

                <div style={styles.fieldGroup}>
                  <label style={styles.label}>Email Address</label>
                  <input
                    type="email"
                    name="email"
                    placeholder="Enter your email"
                    value={form.email}
                    onChange={handleChange}
                    required
                    style={styles.input}
                  />
                </div>

                <div style={styles.fieldGroup}>
                  <label style={styles.label}>Company</label>
                  <input
                    type="text"
                    name="company"
                    placeholder="Enter company name"
                    value={form.company}
                    onChange={handleChange}
                    style={styles.input}
                  />
                </div>

                <div style={styles.fieldGroup}>
                  <label style={styles.label}>Message</label>
                  <textarea
                    name="message"
                    placeholder="Tell us what you need help with"
                    rows="6"
                    value={form.message}
                    onChange={handleChange}
                    required
                    style={styles.textarea}
                  />
                </div>

                {error && <p style={styles.error}>{error}</p>}
                {message && <p style={styles.success}>{message}</p>}

                <button type="submit" disabled={loading} style={styles.submitBtn}>
                  {loading ? "Sending..." : "Send Message"}
                </button>
              </form>
            </div>

            <div style={styles.infoColumn}>
              <div style={styles.infoCard}>
                <h2 style={styles.sectionTitle}>Contact details</h2>
                <p style={styles.sectionText}>
                  You can keep this simple for now and later connect it with real inbox, CRM, or support flows.
                </p>

                <div style={styles.contactList}>
                  {contactItems.map((item) => (
                    <div key={item.title} style={styles.contactItem}>
                      <h3 style={styles.contactTitle}>{item.title}</h3>
                      <p style={styles.contactText}>{item.text}</p>
                      <p style={styles.contactValue}>{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div style={styles.helpCard}>
                <h3 style={styles.helpTitle}>Need faster onboarding?</h3>
                <p style={styles.helpText}>
                  Start with pricing or create an account first, then use contact for product-specific questions.
                </p>

                <div style={styles.helpButtons}>
                  <Link to="/pricing" style={styles.secondaryBtn}>
                    View Pricing
                  </Link>
                  <Link to="/register" style={styles.primaryBtn}>
                    Create Account
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.faqSection}>
        <div style={styles.containerSmall}>
          <div style={styles.faqBox}>
            <h2 style={styles.sectionTitleCenter}>What users may contact you for</h2>

            <div style={styles.faqGrid}>
              <div style={styles.faqCard}>
                <h3 style={styles.faqTitle}>Plan selection</h3>
                <p style={styles.faqText}>
                  Help users choose between Starter, Pro, and Agency plans based on their SEO workload.
                </p>
              </div>

              <div style={styles.faqCard}>
                <h3 style={styles.faqTitle}>Product demo</h3>
                <p style={styles.faqText}>
                  Explain how projects, keywords, reports, audits, and competitors fit together.
                </p>
              </div>

              <div style={styles.faqCard}>
                <h3 style={styles.faqTitle}>Support requests</h3>
                <p style={styles.faqText}>
                  Handle login questions, setup confusion, feature guidance, or reporting issues.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </PublicLayout>
  );
}

const styles = {
  heroSection: {
    background: "linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
    padding: "72px 20px 50px",
  },
  mainSection: {
    background: "#f8fafc",
    padding: "20px 20px 60px",
  },
  faqSection: {
    background: "#ffffff",
    padding: "0 20px 80px",
  },
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
  },
  containerSmall: {
    maxWidth: "920px",
    margin: "0 auto",
  },
  heroContent: {
    maxWidth: "860px",
    margin: "0 auto",
    textAlign: "center",
  },
  badge: {
    display: "inline-block",
    background: "#dbeafe",
    color: "#1d4ed8",
    padding: "8px 14px",
    borderRadius: "999px",
    fontSize: "14px",
    fontWeight: 700,
    marginBottom: "18px",
  },
  heroTitle: {
    fontSize: "46px",
    fontWeight: 800,
    lineHeight: 1.15,
    color: "#0f172a",
    marginBottom: "18px",
  },
  heroText: {
    fontSize: "18px",
    lineHeight: 1.7,
    color: "#475569",
    maxWidth: "760px",
    margin: "0 auto",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1.1fr 0.9fr",
    gap: "24px",
    alignItems: "start",
  },
  formCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "20px",
    padding: "30px",
    boxShadow: "0 10px 30px rgba(15, 23, 42, 0.05)",
  },
  infoColumn: {
    display: "flex",
    flexDirection: "column",
    gap: "24px",
  },
  infoCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "20px",
    padding: "30px",
    boxShadow: "0 10px 30px rgba(15, 23, 42, 0.05)",
  },
  helpCard: {
    background: "#0f172a",
    color: "#ffffff",
    borderRadius: "20px",
    padding: "28px",
    boxShadow: "0 12px 30px rgba(15, 23, 42, 0.12)",
  },
  sectionTitle: {
    fontSize: "30px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "12px",
  },
  sectionTitleCenter: {
    fontSize: "30px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "24px",
    textAlign: "center",
  },
  sectionText: {
    fontSize: "16px",
    lineHeight: 1.7,
    color: "#64748b",
    marginBottom: "24px",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  label: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#334155",
  },
  input: {
    height: "48px",
    borderRadius: "12px",
    border: "1px solid #cbd5e1",
    padding: "0 14px",
    fontSize: "15px",
    outline: "none",
    background: "#ffffff",
    color: "#0f172a",
  },
  textarea: {
    borderRadius: "12px",
    border: "1px solid #cbd5e1",
    padding: "14px",
    fontSize: "15px",
    outline: "none",
    background: "#ffffff",
    color: "#0f172a",
    resize: "vertical",
  },
  submitBtn: {
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    borderRadius: "12px",
    padding: "14px 18px",
    fontSize: "15px",
    fontWeight: 700,
    cursor: "pointer",
    marginTop: "6px",
  },
  error: {
    color: "#d92d20",
    margin: 0,
    fontSize: "14px",
  },
  success: {
    color: "#059669",
    margin: 0,
    fontSize: "14px",
  },
  contactList: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  contactItem: {
    padding: "18px",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "14px",
  },
  contactTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "8px",
  },
  contactText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
    marginBottom: "8px",
  },
  contactValue: {
    fontSize: "15px",
    fontWeight: 700,
    color: "#1d4ed8",
  },
  helpTitle: {
    fontSize: "24px",
    fontWeight: 800,
    marginBottom: "10px",
  },
  helpText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "rgba(255,255,255,0.88)",
    marginBottom: "20px",
  },
  helpButtons: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
  },
  primaryBtn: {
    textDecoration: "none",
    background: "#ffffff",
    color: "#0f172a",
    padding: "12px 18px",
    borderRadius: "12px",
    fontWeight: 700,
    fontSize: "14px",
  },
  secondaryBtn: {
    textDecoration: "none",
    background: "rgba(255,255,255,0.08)",
    color: "#ffffff",
    padding: "12px 18px",
    borderRadius: "12px",
    fontWeight: 700,
    fontSize: "14px",
    border: "1px solid rgba(255,255,255,0.18)",
  },
  faqBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "24px",
    padding: "34px",
  },
  faqGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "20px",
  },
  faqCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "16px",
    padding: "22px",
  },
  faqTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "10px",
  },
  faqText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
  },
};

export default ContactPage;