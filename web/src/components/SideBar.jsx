import { NavLink, Link, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChartLine,
  faFolderOpen,
  faMagnifyingGlassChart,
  faBug,
  faUsersViewfinder,
  faFileLines,
  faFileInvoiceDollar,
} from '@fortawesome/free-solid-svg-icons';

const navItems = [
  { to: '/app', label: 'Dashboard', icon: faChartLine },
  { to: '/app/projects', label: 'Projects', icon: faFolderOpen },
  { to: '/app/keywords', label: 'Keywords', icon: faMagnifyingGlassChart },
  { to: '/app/audit', label: 'Audit', icon: faBug },
  { to: '/app/competitors', label: 'Competitors', icon: faUsersViewfinder },
  { to: '/app/reports', label: 'Reports', icon: faFileLines },
  { to: '/app/billing', label: 'Billing', icon: faFileInvoiceDollar },
];

function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
      <Link to="/" className="flex items-center gap-3 border-b border-slate-200 px-6 py-5 cursor-pointer transition hover:bg-brand-700 hover:text-white">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
          <FontAwesomeIcon icon={faChartLine} className="text-lg" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Helping Suite</p>
          <h1 className="text-lg font-bold text-slate-900">RankCare</h1>
        </div>
      </Link>

      <nav className="flex-1 space-y-2 px-4 py-6">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/app'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition ${
                isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            <FontAwesomeIcon icon={item.icon} className="w-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="m-4 rounded-3xl bg-slate-900 p-5 text-white">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Upgrade</p>
        <h3 className="mt-2 text-lg font-semibold">Agency mode</h3>
        <p className="mt-2 text-sm text-slate-300">
          White-label reporting, more tracked keywords, and client workspaces.
        </p>
        <button
          onClick={() => navigate('/pricing')}
          className="mt-4 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
        >
          Explore plans
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;