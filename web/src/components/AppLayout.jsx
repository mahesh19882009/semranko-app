import { useEffect, useState, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { fetchProjects } from '../features/projects/projectsSlice';
import { fetchCurrentPricing } from '../features/pricing/pricingSlice';

function AppLayout() {
  const dispatch = useDispatch();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    dispatch(fetchProjects());
    dispatch(fetchCurrentPricing());
  }, [dispatch]);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex min-h-screen">
        <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((prev) => !prev)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />
          <main className="flex-1 px-4 py-6 sm:px-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
