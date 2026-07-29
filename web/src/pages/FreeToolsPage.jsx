import { Link, useNavigate } from "react-router-dom";
import PublicLayout from "../components/PublicLayout";
import Button from "../components/ui/Button";

function FreeToolsPage() {

  const navigate = useNavigate();

  const tools = [
    {
      name: "Meta Tag Checker",
      description:
        "Check title tags, meta descriptions, and missing metadata for any page URL.",
      status: "Coming Soon",
    },
    {
      name: "Keyword Density Checker",
      description:
        "Analyze how often a keyword appears in page content and spot overuse or weak coverage.",
      status: "Coming Soon",
    },
    {
      name: "SERP Preview Tool",
      description:
        "Preview how your page title and meta description may appear in search results.",
      status: "Coming Soon",
    },
    {
      name: "Robots.txt Tester",
      description:
        "Validate robots directives and confirm whether important URLs are blocked or allowed.",
      status: "Coming Soon",
    },
    {
      name: "Heading Structure Checker",
      description:
        "Review H1, H2, and H3 hierarchy to find weak page structure and SEO issues quickly.",
      status: "Coming Soon",
    },
    {
      name: "URL Slug Analyzer",
      description:
        "Evaluate slug length, readability, and keyword relevance for better on-page SEO structure.",
      status: "Coming Soon",
    },
  ];

  const navigateHandler = (path) => {
    navigate(path);
  }


  return (
    <PublicLayout>
      <section style={styles.heroSection}>
        <div style={styles.container}>
          <div style={styles.heroContent}>
            <span style={styles.badge}>Free SEO Tools</span>
            <h1 style={styles.heroTitle}>Useful SEO tools to help teams audit pages faster</h1>
            <p style={styles.heroText}>
              RankCare free tools are designed to help marketers, website owners, and SEO teams check
              common on-page issues before moving into deeper tracking and reporting workflows.
            </p>

            <div style={styles.heroButtons}>
              <Button onClick={() => navigateHandler('/register')} variant="primary">
                Create Free Account
              </Button>
              <Button onClick={() => navigateHandler('/pricing')} variant="outline">
                View Pricing
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.toolsSection}>
        <div style={styles.container}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Planned free tools</h2>
            <p style={styles.sectionText}>
              Start with lightweight SEO checks, then move into full keyword tracking, reporting, and
              project workflows inside RankCare.
            </p>
          </div>

          <div style={styles.grid}>
            {tools.map((tool) => (
              <div key={tool.name} style={styles.card}>
                <div style={styles.cardTop}>
                  <span style={styles.status}>{tool.status}</span>
                </div>

                <h3 style={styles.cardTitle}>{tool.name}</h3>
                <p style={styles.cardDescription}>{tool.description}</p>

                <div style={styles.cardFooter}>
                  <Button style={styles.cardButton} disabled>
                    Preview Tool
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={styles.whySection}>
        <div style={styles.container}>
          <div style={styles.whyBox}>
            <h2 style={styles.sectionTitle}>Why free tools matter</h2>

            <div style={styles.whyGrid}>
              <div style={styles.whyItem}>
                <h3 style={styles.whyTitle}>Quick checks</h3>
                <p style={styles.whyText}>
                  Teams can quickly inspect page-level SEO issues without setting up a full project first.
                </p>
              </div>

              <div style={styles.whyItem}>
                <h3 style={styles.whyTitle}>Top-of-funnel traffic</h3>
                <p style={styles.whyText}>
                  Useful tools attract website owners searching for fast answers and convert them into product users.
                </p>
              </div>

              <div style={styles.whyItem}>
                <h3 style={styles.whyTitle}>Natural product fit</h3>
                <p style={styles.whyText}>
                  Once users trust the free checks, they are more likely to use rank tracking and reporting features.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section style={styles.ctaSection}>
        <div style={styles.containerSmall}>
          <div style={styles.ctaBox}>
            <h2 style={styles.ctaTitle}>Use free tools now, scale into full SEO tracking later</h2>
            <p style={styles.ctaText}>
              Start with lightweight page analysis, then upgrade to projects, keyword monitoring,
              competitor tracking, and reports inside RankCare.
            </p>

            <div style={styles.ctaButtons}>
              <Button onClick={() => navigateHandler('/register')} variant="danger">
                Get Started
              </Button>
              <Button onClick={() => navigateHandler('/contact')} variant="outline">
                Contact Us
              </Button>
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
  toolsSection: {
    background: "#f8fafc",
    padding: "20px 20px 60px",
  },
  whySection: {
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
  sectionHeader: {
    maxWidth: "760px",
    marginBottom: "28px",
  },
  sectionTitle: {
    fontSize: "32px",
    fontWeight: 800,
    color: "#0f172a",
    marginBottom: "12px",
  },
  sectionText: {
    fontSize: "17px",
    color: "#64748b",
    lineHeight: 1.7,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "24px",
  },
  card: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "20px",
    padding: "24px",
    boxShadow: "0 10px 30px rgba(15, 23, 42, 0.05)",
    display: "flex",
    flexDirection: "column",
    minHeight: "250px",
  },
  cardTop: {
    marginBottom: "18px",
  },
  status: {
    display: "inline-block",
    background: "#fef3c7",
    color: "#92400e",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
  },
  cardTitle: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "12px",
  },
  cardDescription: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
    flex: 1,
  },
  cardFooter: {
    marginTop: "22px",
  },
  cardButton: {
    width: "100%",
    background: "#eff6ff",
    color: "#1d4ed8",
    border: "none",
    borderRadius: "12px",
    padding: "12px 16px",
    fontSize: "15px",
    fontWeight: 700,
    cursor: "pointer",
  },
  whyBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "24px",
    padding: "36px",
  },
  whyGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "20px",
    marginTop: "10px",
  },
  whyItem: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "16px",
    padding: "22px",
  },
  whyTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: "10px",
  },
  whyText: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#64748b",
  },
  ctaBox: {
    background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
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
    color: "rgba(255,255,255,0.88)",
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
    color: "#0f172a",
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

export default FreeToolsPage;