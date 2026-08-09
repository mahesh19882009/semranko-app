'use client'
import { Link, useNavigate } from "../lib/navigation";
import Button from "../components/ui/Button";

function HomePage() {
  const navigate = useNavigate();
  const navigateHandler = (path) => {
    navigate(path);
  }
  const features = [
    {
      title: "Track keyword performance",
      description:
        "Monitor keyword positions across projects and keep a close eye on ranking movement over time.",
    },
    {
      title: "Manage SEO projects",
      description:
        "Organize domains, keywords, reports, audits, and competitor tracking inside one workflow.",
    },
    {
      title: "Generate useful reports",
      description:
        "Create clear SEO reports for internal review or client communication without scattered tools.",
    },
    {
      title: "Watch competitors",
      description:
        "Compare visibility and ranking progress against competitors and spot movement faster.",
    },
  ];

  const steps = [
    "Create a project and add your domain",
    "Add the keywords you want to monitor",
    "Review rankings, reports, and competitor updates",
  ];

  const stats = [
    { label: "Projects", value: "Multi-project" },
    { label: "Tracking", value: "Weekly rank checks" },
    { label: "Reports", value: "Client-ready workflow" },
    { label: "Focus", value: "SEO workflows" },
  ];

  return (
    <>
      <section style={styles.heroSection}>
        <div style={styles.container}>
          <div style={styles.heroGrid}>
            <div style={styles.heroLeft}>
              <span style={styles.badge}>RankCare SEO Platform</span>
              <h1 style={styles.heroTitle}>
                Track rankings, monitor competitors, and manage SEO work from one place
              </h1>
              <p style={styles.heroText}>
                RankCare is built for marketers and agencies that want a cleaner way
                to manage keyword tracking, reports, audits, and project-level SEO workflows.
              </p>

              <div style={styles.heroButtons}>
                <Button onClick={() => navigateHandler('/register')} variant="primary">
                  Get Started
                </Button>
                <Button onClick={() => navigateHandler('/pricing')} variant="outline">
                  View Pricing
                </Button>
              </div>

              <div style={styles.statsGrid}>
                {stats.map((item) => (
                  <div key={item.label} style={styles.statCard}>
                    <div style={styles.statValue}>{item.value}</div>
                    <div style={styles.statLabel}>{item.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={styles.heroRight}>
              <div style={styles.mockupCard}>
                <div style={styles.mockupHeader}>
                  <span style={styles.mockupDotRed}></span>
                  <span style={styles.mockupDotYellow}></span>
                  <span style={styles.mockupDotGreen}></span>
                </div>

                <div style={styles.mockupBody}>
                  <div style={styles.mockupTopRow}>
                    <div style={styles.metricCard}>
                      <p style={styles.metricLabel}>Tracked Keywords</p>
                      <h3 style={styles.metricValue}>1,240</h3>
                    </div>
                    <div style={styles.metricCard}>
                      <p style={styles.metricLabel}>Visibility Change</p>
                      <h3 style={styles.metricValueGreen}>+12.6%</h3>
                    </div>
                  </div>

                  <div style={styles.chartCard}>
                    <p style={styles.metricLabel}>Rank Trend</p>
                    <div style={styles.chartBars}>
                      <span style={{ ...styles.bar, height: "52px" }}></span>
                      <span style={{ ...styles.bar, height: "70px" }}></span>
                      <span style={{ ...styles.bar, height: "62px" }}></span>
                      <span style={{ ...styles.bar, height: "88px" }}></span>
                      <span style={{ ...styles.bar, height: "98px" }}></span>
                      <span style={{ ...styles.bar, height: "82px" }}></span>
                      <span style={{ ...styles.bar, height: "112px" }}></span>
                    </div>
                  </div>

                  <div style={styles.activityCard}>
                    <p style={styles.metricLabel}>Recent Movement</p>
                    <div style={styles.activityItem}>
                      <span>best seo tools</span>
                      <span style={styles.up}>↑ 4</span>
                    </div>
                    <div style={styles.activityItem}>
                      <span>rank tracker app</span>
                      <span style={styles.up}>↑ 7</span>
                    </div>
                    <div style={styles.activityItem}>
                      <span>seo report software</span>
                      <span style={styles.down}>↓ 2</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.featureSection}>
        <div style={styles.container}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Built around the real SEO workflow</h2>
            <p style={styles.sectionText}>
              Instead of jumping between disconnected tools, RankCare keeps the core SEO workflow inside one platform.
            </p>
          </div>

          <div style={styles.featureGrid}>
            {features.map((feature) => (
              <div key={feature.title} style={styles.featureCard}>
                <h3 style={styles.featureTitle}>{feature.title}</h3>
                <p style={styles.featureText}>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={styles.stepsSection}>
        <div style={styles.container}>
          <div style={styles.stepsBox}>
            <div style={styles.stepsLeft}>
              <h2 style={styles.sectionTitle}>How it works</h2>
              <p style={styles.sectionText}>
                Start simple, then expand from tracking into reporting, audits, and competitor analysis.
              </p>
            </div>

            <div style={styles.stepsRight}>
              {steps.map((step, index) => (
                <div key={step} style={styles.stepItem}>
                  <div style={styles.stepNumber}>0{index + 1}</div>
                  <div style={styles.stepText}>{step}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section style={styles.ctaSection}>
        <div style={styles.containerSmall}>
          <div style={styles.ctaBox}>
            <h2 style={styles.ctaTitle}>Bring your SEO workflow into one clean system</h2>
            <p style={styles.ctaText}>
              Use RankCare to manage projects, monitor keywords, compare competitors, and create reports
              without relying on scattered tools.
            </p>

            <div style={styles.ctaButtons}>
              <Button onClick={() => navigateHandler('/register')} variant="danger">
                Create Account
              </Button>
              <Button onClick={() => navigateHandler('/pricing')} variant="outline">
                Compare Plans
              </Button>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

const styles = {
  heroSection: {
    background: "linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
    padding: "72px 20px 60px",
  },
  featureSection: {
    background: "#f8fafc",
    padding: "20px 20px 60px",
  },
  stepsSection: {
    background: "#ffffff",
    padding: "0 20px 60px",
  },
  linkSection: {
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
  heroGrid: {
    display: "grid",
    gridTemplateColumns: "1.1fr 0.9fr",
    gap: "28px",
    alignItems: "center",
  },
  heroLeft: {},
  heroRight: {},
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
    fontSize: "52px",
    fontWeight: 800,
    lineHeight: 1.1,
    color: "#0f172a",
    marginBottom: "18px",
  },
  heroText: {
    fontSize: "18px",
    lineHeight: 1.8,
    color: "#475569",
    maxWidth: "680px",
    marginBottom: "28px",
  },
  heroButtons: {
    display: "flex",
    gap: "14px",
    flexWrap: "wrap",
    marginBottom: "30px",
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
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: "14px",
  },
  statCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "16px",
    padding: "18px",
    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
  },
  statValue: {
    fontSize: "18px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "6px",
  },
  statLabel: {
    fontSize: "14px",
    color: "#64748b",
  },
  mockupCard: {
    background: "#0f172a",
    borderRadius: "24px",
    padding: "18px",
    boxShadow: "0 20px 40px rgba(15, 23, 42, 0.18)",
  },
  mockupHeader: {
    display: "flex",
    gap: "8px",
    marginBottom: "18px",
  },
  mockupDotRed: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    background: "#f87171",
    display: "inline-block",
  },
  mockupDotYellow: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    background: "#fbbf24",
    display: "inline-block",
  },
  mockupDotGreen: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    background: "#4ade80",
    display: "inline-block",
  },
  mockupBody: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  mockupTopRow: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: "14px",
  },
  metricCard: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "16px",
    padding: "18px",
  },
  metricLabel: {
    fontSize: "13px",
    color: "rgba(255,255,255,0.65)",
    marginBottom: "10px",
  },
  metricValue: {
    fontSize: "28px",
    color: "#ffffff",
    fontWeight: 800,
  },
  metricValueGreen: {
    fontSize: "28px",
    color: "#4ade80",
    fontWeight: 800,
  },
  chartCard: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "16px",
    padding: "18px",
  },
  chartBars: {
    display: "flex",
    alignItems: "end",
    gap: "10px",
    height: "120px",
    marginTop: "18px",
  },
  bar: {
    flex: 1,
    borderRadius: "10px 10px 0 0",
    background: "linear-gradient(180deg, #60a5fa 0%, #2563eb 100%)",
  },
  activityCard: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "16px",
    padding: "18px",
  },
  activityItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    color: "#ffffff",
    padding: "10px 0",
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    fontSize: "14px",
  },
  up: {
    color: "#4ade80",
    fontWeight: 700,
  },
  down: {
    color: "#f87171",
    fontWeight: 700,
  },
  sectionHeader: {
    maxWidth: "760px",
    marginBottom: "28px",
  },
  sectionTitle: {
    fontSize: "34px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "12px",
  },
  sectionText: {
    fontSize: "17px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  featureGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "24px",
  },
  featureCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "18px",
    padding: "24px",
    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
  },
  featureTitle: {
    fontSize: "20px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "12px",
  },
  featureText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  stepsBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "24px",
    padding: "34px",
    display: "grid",
    gridTemplateColumns: "0.9fr 1.1fr",
    gap: "24px",
    alignItems: "start",
  },
  stepsLeft: {},
  stepsRight: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  stepItem: {
    display: "flex",
    gap: "16px",
    alignItems: "center",
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "16px",
    padding: "18px",
  },
  stepNumber: {
    width: "46px",
    height: "46px",
    borderRadius: "50%",
    background: "#dbeafe",
    color: "#1d4ed8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 800,
    fontSize: "16px",
    flexShrink: 0,
  },
  stepText: {
    fontSize: "15px",
    color: "#334155",
    lineHeight: 1.6,
    fontWeight: 500,
  },
  linkGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "24px",
  },
  linkCard: {
    textDecoration: "none",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "18px",
    padding: "24px",
    display: "block",
  },
  linkTitle: {
    fontSize: "20px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "10px",
  },
  linkText: {
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

export default HomePage;