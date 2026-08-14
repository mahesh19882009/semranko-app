'use client'
import { NavLink, Link } from '../lib/navigation';
import { ArrowUpRight, BarChart3, FileText, FolderKanban, Lightbulb, Settings, Sparkles, X } from 'lucide-react';
import IconButton from './ui/IconButton';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/keywords', label: 'Keywords', icon: Sparkles },
  { to: '/keyword-research', label: 'Keyword Research', icon: Lightbulb },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/billing', label: 'Billing & credits', icon: FileText },
];

function Sidebar({ open, mobileOpen, onCloseMobile }) {
  return (
    <>
      {mobileOpen ? <button type="button" aria-label="Close navigation" className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" onClick={onCloseMobile} /> : null}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 shrink-0 flex-col border-r border-border bg-surface shadow-elevated transition-transform duration-200 lg:sticky lg:z-20 lg:translate-x-0 lg:shadow-none ${open ? 'lg:w-72' : 'lg:w-16'} ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
        aria-label="Primary navigation"
      >
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-5">
        <Link
          to="/"
          className={`h-[46px] flex items-center gap-3 overflow-hidden transition ${open ? 'px-2' : 'justify-center px-0'
            }`}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
          </div>
          {open && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-text-muted">SEO workspace</p>
              <h1 className="text-lg font-bold text-slate-900">RankCare</h1>
            </div>
          )}
        </Link>
        <IconButton label="Close navigation" variant="ghost" className="lg:hidden" onClick={onCloseMobile}><X className="h-5 w-5" /></IconButton>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <nav className="px-3 py-6 flex flex-col">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/dashboard'}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition focus:outline-none focus:ring-4 focus:ring-brand-100 ${isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'
                  } ${!open ? 'lg:justify-center' : ''}`
                }
                title={!open ? item.label : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className={open ? '' : 'lg:sr-only'}>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>
      <div className="border-t border-border p-3">
        <NavLink to="/dashboard/settings" onClick={onCloseMobile} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-text-secondary hover:bg-surface-muted'} ${!open ? 'lg:justify-center' : ''}`} title={!open ? 'Settings' : undefined}>
          <Settings className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className={open ? '' : 'lg:sr-only'}>Settings</span>
        </NavLink>
        <Link to="/billing" onClick={onCloseMobile} className={`mt-2 flex items-center justify-center rounded-xl bg-brand-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 focus:outline-none focus:ring-4 focus:ring-brand-200 ${!open ? 'lg:px-2' : ''}`} title={!open ? 'Upgrade plan' : undefined}>
          <span className={open ? '' : 'lg:sr-only'}>Upgrade plan</span><ArrowUpRight className={`h-4 w-4 ${open ? '' : 'lg:block'}`} aria-hidden="true" />
        </Link>
      </div>
      </aside>
    </>
  );
}

export default Sidebar;
