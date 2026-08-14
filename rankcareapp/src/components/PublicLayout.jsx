'use client'
import { Link, useLocation, useNavigate } from "../lib/navigation";
import { useEffect, useState } from "react";
import { BarChart3, Menu, X } from 'lucide-react';
import { isAuthenticated, logoutUser } from "../utils/auth";
import Button from "./ui/Button";
import { logoutApi } from '../lib/api';
import { brand, contactHref } from '../config/brand';

function PublicLayout({ children }) {
  const navigate = useNavigate();
  const navigateHandler = (path) => {
    navigate(path);
  }
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const navItems = [
    ['/', 'Home'], ['/features', 'Features'], ['/pricing', 'Pricing'], ['/about', 'About'], ['/faq', 'FAQ'], ['/contact', 'Contact'],
  ];

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

  useEffect(() => {
    const closeOnEscape = (event) => { if (event.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
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
    <div className="flex min-h-screen flex-col bg-surface-subtle text-text-primary">
      <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="inline-flex items-center gap-2 font-bold tracking-tight text-text-primary" onClick={() => setMenuOpen(false)}><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white"><BarChart3 className="h-4 w-4" aria-hidden="true" /></span>{brand.name}</Link>
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">{navItems.map(([to, label]) => <Link key={to} to={to} className={`rounded-lg px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-4 focus:ring-brand-100 ${location.pathname === to ? 'bg-brand-50 text-brand-700' : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'}`}>{label}</Link>)}</nav>
          <div className="hidden items-center gap-2 lg:flex">{authenticated ? <><Button size="sm" onClick={navigateToDashboard}>Dashboard</Button><Button size="sm" variant="outline" onClick={handleLogout}>Log out</Button></> : <><Link to="/login" className="rounded-lg px-3 py-2 text-sm font-semibold text-text-secondary focus:outline-none focus:ring-4 focus:ring-brand-100">Login</Link><Link to="/register"><Button size="sm">Get started</Button></Link></>}</div>
          <button type="button" className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-text-secondary focus:outline-none focus:ring-4 focus:ring-brand-100 lg:hidden" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
        </div>
        {menuOpen ? <div className="border-t border-border bg-surface px-4 py-4 lg:hidden"><nav className="grid gap-1" aria-label="Mobile navigation">{navItems.map(([to, label]) => <Link key={to} to={to} onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-2.5 text-sm font-medium text-text-secondary hover:bg-surface-muted">{label}</Link>)}<div className="mt-3 flex gap-2 border-t border-border pt-3">{authenticated ? <><Button className="flex-1" onClick={navigateToDashboard}>Dashboard</Button><Button variant="outline" onClick={handleLogout}>Log out</Button></> : <><Link className="flex-1" to="/login" onClick={() => setMenuOpen(false)}><Button className="w-full" variant="outline">Login</Button></Link><Link className="flex-1" to="/register" onClick={() => setMenuOpen(false)}><Button className="w-full">Get started</Button></Link></>}</div></nav></div> : null}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-border bg-surface">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-2 lg:grid-cols-5 lg:px-8">
          <div className="lg:col-span-1"><p className="font-bold text-text-primary">{brand.name}</p><p className="mt-2 text-sm leading-6 text-text-secondary">Clear rank tracking and practical SEO intelligence.</p></div>
          <FooterGroup title="Product" links={[['Features', '/features'], ['Pricing', '/pricing']]} />
          <FooterGroup title="Company" links={[['About', '/about'], ['Contact', '/contact']]} />
          <FooterGroup title="Resources" links={[['FAQ', '/faq']]} />
          <FooterGroup title="Legal" links={[['Privacy', '/privacy'], ['Terms', '/terms'], ['Refund & cancellation', '/refund-policy']]} />
        </div>
        <div className="border-t border-border"><div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-5 text-xs text-text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"><span>© 2026 {brand.name}. All rights reserved.</span><span>{brand.supportEmail ? <a className="underline hover:text-text-primary" href={contactHref(brand.supportEmail)}>Support</a> : 'Support contact to be confirmed before launch.'}</span></div></div>
      </footer>
    </div>
  );
}

function FooterGroup({ title, links }) { return <div><h2 className="text-sm font-semibold text-text-primary">{title}</h2><ul className="mt-3 space-y-2">{links.map(([label, to]) => <li key={to}><Link to={to} className="text-sm text-text-secondary hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-200">{label}</Link></li>)}</ul></div>; }

export default PublicLayout;
