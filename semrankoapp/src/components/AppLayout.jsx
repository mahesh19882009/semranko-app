'use client'
import { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import SideBar from './SideBar';
import TopBar from './TopBar';
import { fetchProjects } from '../features/projects/projectsSlice';
import { fetchCurrentPricing } from '../features/pricing/pricingSlice';

function AppLayout({ children }) {
  const dispatch = useDispatch();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchProjects());
    dispatch(fetchCurrentPricing());
  }, [dispatch]);

  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setMobileNavigationOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex min-h-screen">
        <SideBar
          open={sidebarOpen}
          mobileOpen={mobileNavigationOpen}
          onCloseMobile={() => setMobileNavigationOpen(false)}
        />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            onToggleSidebar={() => {
              if (window.matchMedia('(min-width: 1024px)').matches) {
                setSidebarOpen((prev) => !prev);
              } else {
                setMobileNavigationOpen((prev) => !prev);
              }
            }}
          />
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
