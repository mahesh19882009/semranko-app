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

  useEffect(() => {
    dispatch(fetchProjects());
    dispatch(fetchCurrentPricing());
  }, [dispatch]);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex min-h-screen">
        <SideBar open={sidebarOpen} onToggle={() => setSidebarOpen((prev) => !prev)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />
          <main className="flex-1 px-4 py-6 sm:px-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
