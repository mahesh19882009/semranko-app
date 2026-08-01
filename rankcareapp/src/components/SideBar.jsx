'use client'
import { NavLink, Link } from '../lib/navigation';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChartLine,
  faFolderOpen,
  faMagnifyingGlassChart,
  faLightbulb,
  faUsersViewfinder,
  faListCheck,
  faBrain,
  faFileInvoiceDollar,
} from '@fortawesome/free-solid-svg-icons';
import Button from './ui/Button';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: faChartLine },
  { to: '/projects', label: 'Projects', icon: faFolderOpen },
  { to: '/keywords', label: 'Keywords', icon: faMagnifyingGlassChart },
  { to: '/keyword-research', label: 'Keyword Research', icon: faLightbulb },
  { to: '/competitors', label: 'Competitors', icon: faUsersViewfinder },
  { to: '/keyword-lists', label: 'Keyword Lists', icon: faListCheck },
  { to: '/aio', label: 'AIO Overview', icon: faBrain },
];

function Sidebar({ open, onToggle }) {
  return (
    <aside
      className={`h-[100vh] sticky top-0 shrink-0 border-r border-slate-200 bg-white transition-all duration-300 ${open ? 'w-72' : 'w-16'
        } flex flex-col`}
    >
      <div className="shrink-0 flex items-center justify-between border-b border-slate-200 px-4 py-5">
        <Link
          to="/"
          className={`h-[46px] flex items-center gap-3 overflow-hidden transition ${open ? 'px-2' : 'justify-center px-0'
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
        <nav className="px-3 py-6 flex flex-col">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/dashboard'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition ${isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                } ${!open ? 'justify-center' : ''}`
              }
              title={!open ? item.label : undefined}
            >
              <FontAwesomeIcon icon={item.icon} className="w-4 mr-2" />
              {open && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}

export default Sidebar;
