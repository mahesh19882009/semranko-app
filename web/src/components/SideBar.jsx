import { NavLink, Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChartLine,
  faFolderOpen,
  faMagnifyingGlassChart,
  faLightbulb,
  faBug,
  faUsersViewfinder,
  faFileLines,
  faFileInvoiceDollar,
  faKey,
  faCalendar,
  faUsers,
  faBars,
} from '@fortawesome/free-solid-svg-icons';
import Button from './ui/Button';

const navItems = [
  { to: '/app', label: 'Dashboard', icon: faChartLine },
  { to: '/app/projects', label: 'Projects', icon: faFolderOpen },
  { to: '/app/keywords', label: 'Keywords', icon: faMagnifyingGlassChart },
  { to: '/app/keyword-research', label: 'Keyword Research', icon: faLightbulb },
  { to: '/app/audit', label: 'Audit', icon: faBug },
  { to: '/app/competitors', label: 'Competitors', icon: faUsersViewfinder },
  { to: '/app/reports', label: 'Reports', icon: faFileLines },
  { to: '/app/scheduled-reports', label: 'Scheduled Reports', icon: faCalendar },
  { to: '/app/teams', label: 'Teams', icon: faUsers },
  { to: '/app/agency-dashboard', label: 'Agency Dashboard', icon: faChartLine },
  { to: '/app/api-keys', label: 'API Keys', icon: faKey },
  { to: '/app/billing', label: 'Billing', icon: faFileInvoiceDollar },
];

function Sidebar({ open, onToggle }) {
  return (
    <aside
      className={`h-[100vh] sticky top-0 shrink-0 border-r border-slate-200 bg-white transition-all duration-300 ${
        open ? 'w-72' : 'w-16'
      } flex flex-col`}
    >
      <div className="shrink-0 flex items-center justify-between border-b border-slate-200 px-4 py-5">
        <Link
          to="/"
          className={`h-[46px] flex items-center gap-3 overflow-hidden transition ${
            open ? 'px-2' : 'justify-center px-0'
          }`}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
            <FontAwesomeIcon icon={faChartLine} className="text-lg" />
          </div>
          {open && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Helping Suite</p>
              <h1 className="text-lg font-bold text-slate-900">RankCare</h1>
            </div>
          )}
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <nav className="px-3 py-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/app'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                } ${!open ? 'justify-center' : ''}`
              }
              title={!open ? item.label : undefined}
            >
              <FontAwesomeIcon icon={item.icon} className="w-4" />
              {open && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div>
          {open ? (
            <div className={`m-4 rounded-3xl bg-slate-900 p-5 text-white transition-all ${!open ? 'p-3' : ''}`}>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Upgrade</p>
              <h3 className="mt-2 text-lg font-semibold">Agency mode</h3>
              <p className="mt-2 text-sm text-slate-300 mb-3">
                White-label reporting, more tracked keywords, and client workspaces.
              </p>
              <Button
                onClick={() => window.location.href = '/pricing'}
                variant="primary"
              >
                Explore plans
              </Button>
            </div>
          ) : (
            <Button
              onClick={() => window.location.href = '/pricing'}
              className="flex w-full items-center justify-center text-white"
              title="Upgrade"
            >
              <FontAwesomeIcon icon={faFileInvoiceDollar} />
            </Button>
          )}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
