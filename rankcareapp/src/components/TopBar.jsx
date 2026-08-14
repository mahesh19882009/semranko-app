'use client'
import { useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "../lib/navigation";
import { ChevronDown, CircleAlert, LogOut, Menu, Settings, X } from 'lucide-react';
import { getStoredUser, logoutUser } from "../utils/auth";
import { logoutApi } from '../lib/api';
import { formatDate } from "../utils/date";
import { setSelectedProjectId } from "../features/projects/projectsSlice";
import { fetchSubscriptionStatus } from "../features/subscription/subscriptionSlice";

function Topbar({ onToggleSidebar }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const projects = useSelector((state) => state.projects.list);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const subscriptionData = useSelector((state) => state.subscription.data);
  const subscriptionLoading = useSelector((state) => state.subscription.loading);

  const [profileOpen, setProfileOpen] = useState(false);
  const [subscriptionBannerOpen, setSubscriptionBannerOpen] = useState(true);

  const profileRef = useRef(null);

  const storedUser = useMemo(() => getStoredUser(), []);

  const userName = storedUser?.name || "User";
  const userEmail = storedUser?.email || "Admin";

  const initials = userName
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    dispatch(fetchSubscriptionStatus());
  }, [dispatch]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        profileOpen &&
        profileRef.current &&
        !profileRef.current.contains(event.target)
      ) {
        setProfileOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setProfileOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [profileOpen]);

  const handleLogout = async () => {
    try { await logoutApi(); } finally { logoutUser(); }
    setProfileOpen(false);
    navigate("/login", { replace: true });
  };

  const handleSettingsClick = () => {
    setProfileOpen(false);
    navigate("/dashboard/settings");
  };

  const showSubscriptionBanner = subscriptionBannerOpen &&
    subscriptionData?.effectivePlan !== 'free_trial' &&
    (subscriptionData?.isInGracePeriod ||
      subscriptionData?.subscriptionStatus === 'past_due' ||
      subscriptionData?.subscriptionStatus === 'inactive');

  const getBannerMessage = () => {
    if (subscriptionData?.isInGracePeriod) return 'Your paid subscription is in its grace period. Update payment details to avoid interruption.';
    if (subscriptionData?.subscriptionStatus === 'past_due') {
      return 'Your subscription payment is past due. Please update your payment details to avoid service interruption.';
    }
    if (subscriptionData?.subscriptionStatus === 'inactive') {
      return 'Your subscription is inactive. Please upgrade to continue using RankCare.';
    }
    return null;
  };

  const bannerMessage = getBannerMessage();

  return (
    <>
      {showSubscriptionBanner && bannerMessage && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CircleAlert className="h-4 w-4 text-warning-dark" aria-hidden="true" />
              <p className="text-sm font-medium text-amber-800">{bannerMessage}</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/billing')}
                className="text-sm font-semibold text-amber-700 hover:text-amber-900"
              >
                {subscriptionData?.subscriptionStatus === 'past_due'
                  ? 'Update Payment'
                  : subscriptionData?.subscriptionStatus === 'inactive'
                    ? 'Upgrade Now'
                    : 'Upgrade Now'}
              </button>
              <button
                onClick={() => setSubscriptionBannerOpen(false)}
                className="rounded-md text-warning-dark hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-warning"
                aria-label="Dismiss subscription notice"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      )}
      <header
        className="sticky top-0 z-30 border-b border-slate-200 bg-white backdrop-blur"
      >
        <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={onToggleSidebar}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface text-text-secondary focus:outline-none focus:ring-4 focus:ring-brand-100"
              aria-label="Toggle navigation"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>

            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-text-muted">
                Selected project
              </p>

              <select
                value={selectedProjectId || ""}
                onChange={(e) => dispatch(setSelectedProjectId(e.target.value || null))}
                className="mt-1 max-w-[150px] rounded-xl border-0 bg-transparent p-0 text-lg !font-bold !text-[18px] truncate outline-none text-slate-900"
              >
                {projects.length === 0 ? (
                  <option value="">No project</option>
                ) : (
                  projects.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          <div className="relative" ref={profileRef}>
            <button
              type="button"
              onClick={() => setProfileOpen((prev) => !prev)}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 transition hover:border-slate-300 hover:bg-slate-50"
              aria-haspopup="menu"
              aria-expanded={profileOpen}
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">
                {initials}
              </div>

              <div className="hidden text-left sm:block">
                <p className="text-sm font-semibold text-slate-900">
                  {userName}
                </p>
                <p className="text-xs text-slate-500">{userEmail}</p>
              </div>

              <ChevronDown className={`hidden h-4 w-4 text-text-muted transition sm:block ${profileOpen ? "rotate-180" : ""}`} aria-hidden="true" />
            </button>

            {profileOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-3 w-56 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg"
              >
                <div className="border-b border-slate-100 px-4 py-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {userName}
                  </p>
                  <p className="text-xs text-slate-500">{userEmail}</p>
                </div>

                <div className="p-2">
                  <button
                    type="button"
                    onClick={handleSettingsClick}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-900"
                  >
                    <Settings className="h-4 w-4 text-text-muted" aria-hidden="true" />
                    <span>Settings</span>
                  </button>

                  <div className="my-2 border-t border-slate-100" />

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-rose-600 transition hover:bg-rose-50"
                  >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}

export default Topbar;
