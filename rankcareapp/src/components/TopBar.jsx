'use client'
import { useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "../lib/navigation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { getStoredUser, logoutUser } from "../utils/auth";
import { formatDate } from "../utils/date";
import {
  faSearch,
  faChevronDown,
  faBars,
  faRightFromBracket,
  faGear,
  faExclamationTriangle,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { setSelectedProjectId } from "../features/projects/projectsSlice";
import { selectDateRange } from "../features/dashboard/dashboardSelectors";
import { fetchSubscriptionStatus } from "../features/subscription/subscriptionSlice";

function Topbar({ onToggleSidebar }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const projects = useSelector((state) => state.projects.list);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const dateRange = useSelector(selectDateRange);

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

  const handleLogout = () => {
    logoutUser();
    setProfileOpen(false);
    navigate("/", { replace: true });
  };

  const handleSettingsClick = () => {
    setProfileOpen(false);
    navigate("/projects");
  };

  const showSubscriptionBanner = subscriptionBannerOpen &&
    (subscriptionData?.isInGracePeriod || subscriptionData?.subscriptionStatus === 'trialing');

  const getBannerMessage = () => {
    if (subscriptionData?.isInGracePeriod) {
      const graceEnd = new Date(subscriptionData.gracePeriodEndsAt);
      const daysLeft = Math.ceil((graceEnd - new Date()) / (1000 * 60 * 60 * 24));
      return `Your trial has expired. Upgrade within ${daysLeft} day${daysLeft !== 1 ? 's' : ''} to continue using RankCare.`;
    }
    if (subscriptionData?.subscriptionStatus === 'trialing' && subscriptionData?.trialEndsAt) {
      const trialEnd = new Date(subscriptionData.trialEndsAt);
      const daysLeft = Math.ceil((trialEnd - new Date()) / (1000 * 60 * 60 * 24));
      if (daysLeft <= 3) {
        return `Your trial expires in ${daysLeft} day${daysLeft !== 1 ? 's' : ''}. Upgrade now to avoid interruption.`;
      }
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
              <FontAwesomeIcon icon={faExclamationTriangle} className="text-amber-600" />
              <p className="text-sm font-medium text-amber-800">{bannerMessage}</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/billing')}
                className="text-sm font-semibold text-amber-700 hover:text-amber-900"
              >
                Upgrade Now
              </button>
              <button
                onClick={() => setSubscriptionBannerOpen(false)}
                className="text-amber-600 hover:text-amber-800"
              >
                <FontAwesomeIcon icon={faXmark} />
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
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600"
          >
            <FontAwesomeIcon icon={faBars} />
          </button>

          <div>
            <p className="text-xs uppercase tracking-[0.24em text-slate-900">
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

        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => dispatch(setDateRange(e.target.value))}
            className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 outline-none"
          >
            <option>Last 7 days</option>
            <option>Last 30 days</option>
            <option>Last 90 days</option>
          </select>

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

              <FontAwesomeIcon
                icon={faChevronDown}
                className={`hidden text-xs text-slate-400 transition sm:block ${profileOpen ? "rotate-180" : ""
                  }`}
              />
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
                    <FontAwesomeIcon
                      icon={faGear}
                      className="w-4 text-slate-400"
                    />
                    <span>Settings</span>
                  </button>

                  <div className="my-2 border-t border-slate-100" />

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-rose-600 transition hover:bg-rose-50"
                  >
                    <FontAwesomeIcon
                      icon={faRightFromBracket}
                      className="w-4"
                    />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
    </>
  );
}

export default Topbar;
