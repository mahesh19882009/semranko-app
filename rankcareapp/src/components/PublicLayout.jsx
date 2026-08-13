'use client'
import { Link, useLocation, useNavigate } from "../lib/navigation";
import { useEffect, useState } from "react";
import { isAuthenticated, logoutUser } from "../utils/auth";
import Button from "./ui/Button";
import { logoutApi } from '../lib/api';

function PublicLayout({ children }) {
  const navigate = useNavigate();
  const navigateHandler = (path) => {
    navigate(path);
  }
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, [location.pathname]);

  useEffect(() => {
    const handleStorage = () => {
      setAuthenticated(isAuthenticated());
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const handleLogout = async () => {
    try { await logoutApi(); } finally { logoutUser(); }
    setAuthenticated(false);
    navigate("/login", { replace: true });
  };

  const navigateToDashboard = () => {
    navigate("/dashboard");
  };

  return (
    <div style={styles.wrapper}>
      <header style={styles.header}>
        <div style={styles.container}>
          <div style={styles.navbar}>
            <Link to="/" style={styles.logo}>
              RankCare
            </Link>

            <nav style={styles.nav}>
              <Link to="/pricing" style={styles.navLink}>Pricing</Link>

              {authenticated ? (
                <div style={styles.authActions}>
                  <Button type="button" variant="primary" onClick={navigateToDashboard}>
                    Dashboard
                  </Button>
                  <Button type="button" variant="danger" onClick={handleLogout}>
                    Logout
                  </Button>
                </div>
              ) : (
                <div style={styles.authActions}>
                  <Button onClick={() => navigateHandler('/login')} variant="primary">Login</Button>
                  <Button onClick={() => navigateHandler('/register')} variant="danger">Register</Button>
                </div>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main style={styles.main}>{children}</main>

      <footer style={styles.footer}>
        <div style={styles.container}>
          <p style={styles.footerText}>
            © 2026 RankCare. SEO insights, rank tracking, and reporting.
          </p>
        </div>
      </footer>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    background: "#f8fafc",
    color: "#0f172a",
  },
  header: {
    background: "#ffffff",
    borderBottom: "1px solid #e2e8f0",
    position: "sticky",
    top: 0,
    zIndex: 100,
  },
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "0 20px",
  },
  navbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    minHeight: "72px",
    gap: "20px",
    flexWrap: "wrap",
  },
  logo: {
    fontSize: "24px",
    fontWeight: 700,
    color: "#0f172a",
    textDecoration: "none",
  },
  nav: {
    display: "flex",
    alignItems: "center",
    gap: "18px",
    flexWrap: "wrap",
  },
  navLink: {
    color: "#334155",
    textDecoration: "none",
    fontSize: "15px",
    fontWeight: 500,
  },
  main: {
    flex: 1,
  },
  footer: {
    borderTop: "1px solid #e2e8f0",
    background: "#ffffff",
  },
  footerText: {
    padding: "20px 0",
    color: "#64748b",
    fontSize: "14px",
  },
  authActions: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  dashboardBtn: {
    background: "#2563eb",
    color: "#ffffff",
    padding: "10px 16px",
    borderRadius: "10px",
    textDecoration: "none",
    fontSize: "14px",
    fontWeight: 600,
    border: "none",
    cursor: "pointer",
  },
  logoutBtn: {
    background: "#ef4444",
    color: "#ffffff",
    padding: "10px 16px",
    borderRadius: "10px",
    textDecoration: "none",
    fontSize: "14px",
    fontWeight: 600,
    border: "none",
    cursor: "pointer",
  },
};

export default PublicLayout;
