import { Link } from "react-router-dom";
import PublicLayout from "../components/PublicLayout";

function AboutPage() {
  const values = [
    {
      title: "Clarity first",
      description:
        "SEO data tabhi useful hota hai jab teams usse quickly understand kar sakein and action le sakein.",
    },
    {
      title: "Built for execution",
      description:
        "RankCare ka focus sirf tracking nahi, balki projects, reports, audits, and competitor workflows ko ek jagah lana hai.",
    },
    {
      title: "Made to scale",
      description:
        "Chahe solo marketer ho ya agency, product ko aise design kiya gaya hai ki workflow business ke saath grow kare.",
    },
  ];

  const highlights = [
    "Keyword tracking across projects",
    "Competitor monitoring and comparison",
    "SEO reports for teams and clients",
    "Audit-driven workflow support",
    "Public tools plus full product workflow",
    "Future-ready pricing and plan-based growth",
  ];

  return (
    <PublicLayout>
      <section style={styles.heroSection}>
        <div style={styles.container}>
          <div style={styles.heroContent}>
            <span style={styles.badge}>About RankCare</span>
            <h1 style={styles.heroTitle}>A practical SEO workspace for tracking, reporting, and growth</h1>
            <p style={styles.heroText}>
              RankCare is being built as an SEO product that helps teams manage keyword performance,
              reporting, audits, and competitor visibility from one place instead of juggling multiple tools.
            </p>

            <div style={styles.heroButtons}>
              <Link to="/pricing" style={styles.primaryBtn}>
                View Pricing
              </Link>
              <Link to="/contact" style={styles.secondaryBtn}>
                Contact Us
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.storySection}>
        <div style={styles.container}>
          <div style={styles.storyGrid}>
            <div style={styles.storyLeft}>
              <h2 style={styles.sectionTitle}>Why RankCare exists</h2>
              <p style={styles.storyText}>
                SEO teams often work across spreadsheets, disconnected reporting tools, audit utilities,
                and scattered keyword trackers. That makes even basic reporting and follow-up slower than it should be.
              </p>
              <p style={styles.storyText}>
                RankCare is designed to bring those workflows together in a cleaner way so businesses can
                manage projects, monitor rankings, review reports, and make better SEO decisions with less friction.
              </p>
            </div>

            <div style={styles.storyCard}>
              <h3 style={styles.storyCardTitle}>What RankCare is focused on</h3>
              <ul style={styles.highlightList}>
                {highlights.map((item) => (
                  <li key={item} style={styles.highlightItem}>
                    <span style={styles.check}>✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.valuesSection}>
        <div style={styles.container}>
          <div style={styles.sectionHeaderCenter}>
            <h2 style={styles.sectionTitleCenter}>Core product values</h2>
            <p style={styles.sectionTextCenter}>
              RankCare is being shaped around simple product principles that keep the SEO workflow useful and practical.
            </p>
          </div>

          <div style={styles.valuesGrid}>
            {values.map((value) => (
              <div key={value.title} style={styles.valueCard}>
                <h3 style={styles.valueTitle}>{value.title}</h3>
                <p style={styles.valueText}>{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={styles.audienceSection}>
        <div style={styles.container}>
          <div style={styles.audienceBox}>
            <div style={styles.audienceCol}>
              <h2 style={styles.sectionTitle}>Who this is for</h2>
              <p style={styles.storyText}>
                RankCare is suitable for freelancers, in-house marketers, SEO teams, and agencies that
                want better visibility into projects, rankings, and client reporting.
              </p>
            </div>

            <div style={styles.audienceGrid}>
              <div style={styles.audienceCard}>
                <h3 style={styles.audienceTitle}>Freelancers</h3>
                <p style={styles.audienceText}>
                  Track a few projects cleanly and generate reports without overcomplicated setup.
                </p>
              </div>

              <div style={styles.audienceCard}>
                <h3 style={styles.audienceTitle}>Growing teams</h3>
                <p style={styles.audienceText}>
                  Manage rankings, reporting, and audits with a more structured internal workflow.
                </p>
              </div>

              <div style={styles.audienceCard}>
                <h3 style={styles.audienceTitle}>Agencies</h3>
                <p style={styles.audienceText}>
                  Support multiple clients, stronger reporting, and future white-label style delivery.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.ctaSection}>
        <div style={styles.containerSmall}>
          <div style={styles.ctaBox}>
            <h2 style={styles.ctaTitle}>Build your SEO workflow around one clear system</h2>
            <p style={styles.ctaText}>
              Use RankCare to move from scattered tools toward a more organized workflow for keyword
              tracking, reports, competitor checks, and SEO execution.
            </p>

            <div style={styles.ctaButtons}>
              <Link to="/register" style={styles.bigPrimaryBtn}>
                Create Account
              </Link>
              <Link to="/free-tools" style={styles.bigSecondaryBtn}>
                Explore Free Tools
              </Link>
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
  storySection: {
    background: "#f8fafc",
    padding: "20px 20px 60px",
  },
  valuesSection: {
    background: "#ffffff",
    padding: "0 20px 60px",
  },
  audienceSection: {
    background: "#ffffff",
    padding: "0 20px 60px",
  },
  ctaSection: {
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
    fontSize: "48px",
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
    margin: "0 auto 28px",
  },
  heroButtons: {
    display: "flex",
    justifyContent: "center",
    gap: "14px",
    flexWrap: "wrap",
  },
  primaryBtn: {
    textDecoration: "none",
    background: "#2563eb",
    color: "#ffffff",
    padding: "14px 22px",
    borderRadius: "12px",
    fontSize: "15px",
    fontWeight: 700,
  },
  secondaryBtn: {
    textDecoration: "none",
    background: "#ffffff",
    color: "#1d4ed8",
    padding: "14px 22px",
    borderRadius: "12px",
    fontSize: "15px",
    fontWeight: 700,
    border: "1px solid #cbd5e1",
  },
  storyGrid: {
    display: "grid",
    gridTemplateColumns: "1.2fr 0.8fr",
    gap: "24px",
    alignItems: "start",
  },
  storyLeft: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "20px",
    padding: "32px",
    boxShadow: "0 10px 30px rgba(15, 23, 42, 0.05)",
  },
  storyCard: {
    background: "#0f172a",
    color: "#ffffff",
    borderRadius: "20px",
    padding: "32px",
    boxShadow: "0 10px 30px rgba(15, 23, 42, 0.12)",
  },
  storyCardTitle: {
    fontSize: "24px",
    fontWeight: 700,
    marginBottom: "20px",
  },
  sectionTitle: {
    fontSize: "32px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "16px",
  },
  sectionTitleCenter: {
    fontSize: "32px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "12px",
    textAlign: "center",
  },
  sectionHeaderCenter: {
    maxWidth: "760px",
    margin: "0 auto 28px",
    textAlign: "center",
  },
  sectionTextCenter: {
    fontSize: "17px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  storyText: {
    fontSize: "16px",
    lineHeight: 1.8,
    color: "#64748b",
    marginBottom: "16px",
  },
  highlightList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  highlightItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    fontSize: "15px",
    lineHeight: 1.7,
    color: "rgba(255,255,255,0.9)",
  },
  check: {
    color: "#4ade80",
    fontWeight: 800,
    marginTop: "1px",
  },
  valuesGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "24px",
  },
  valueCard: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "18px",
    padding: "26px",
  },
  valueTitle: {
    fontSize: "20px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "12px",
  },
  valueText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  audienceBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "24px",
    padding: "34px",
  },
  audienceCol: {
    maxWidth: "760px",
    marginBottom: "24px",
  },
  audienceGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "20px",
  },
  audienceCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "16px",
    padding: "22px",
  },
  audienceTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "10px",
  },
  audienceText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  ctaBox: {
    background: "linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)",
    borderRadius: "24px",
    padding: "44px 28px",
    textAlign: "center",
    color: "#ffffff",
  },
  ctaTitle: {
    fontSize: "34px",
    fontWeight: 800,
    lineHeight: 1.2,
    marginBottom: "14px",
  },
  ctaText: {
    fontSize: "17px",
    lineHeight: 1.7,
    maxWidth: "700px",
    margin: "0 auto 28px",
    color: "rgba(255,255,255,0.9)",
  },
  ctaButtons: {
    display: "flex",
    justifyContent: "center",
    gap: "14px",
    flexWrap: "wrap",
  },
  bigPrimaryBtn: {
    textDecoration: "none",
    background: "#ffffff",
    color: "#1d4ed8",
    padding: "14px 22px",
    borderRadius: "12px",
    fontWeight: 700,
    fontSize: "15px",
  },
  bigSecondaryBtn: {
    textDecoration: "none",
    background: "rgba(255,255,255,0.10)",
    color: "#ffffff",
    padding: "14px 22px",
    borderRadius: "12px",
    fontWeight: 700,
    fontSize: "15px",
    border: "1px solid rgba(255,255,255,0.18)",
  },
};

export default AboutPage;