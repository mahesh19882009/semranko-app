import { useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { getStoredUser, logoutUser } from "../utils/auth";
import { formatDate } from "../utils/date";
import {
  faBell,
  faSearch,
  faChevronDown,
  faBars,
  faRightFromBracket,
  faGear,
  faFileLines,
  faKey,
  faFolderOpen,
} from "@fortawesome/free-solid-svg-icons";
import { setDateRange } from "../features/dashboard/dashboardSlice";
import { setSelectedProjectId } from "../features/projects/projectsSlice";
import { selectDateRange } from "../features/dashboard/dashboardSelectors";
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../features/notifications/notificationsSlice";
import {
  clearSearch,
  closeSearch,
  fetchSearchResults,
  setSearchQuery,
} from "../features/search/searchSlice";

function Topbar({ onToggleSidebar }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const projects = useSelector((state) => state.projects.list);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const dateRange = useSelector(selectDateRange);
  const notifications = useSelector((state) => state.notifications.items.slice(0, 5));
  const unreadCount = useSelector((state) => state.notifications.unreadCount);
  const notificationsLoading = useSelector((state) => state.notifications.loading);

  const searchQuery = useSelector((state) => state.search.query);
  const searchResults = useSelector((state) => state.search.results);
  const searchLoading = useSelector((state) => state.search.loading);
  const searchError = useSelector((state) => state.search.error);
  const searchOpen = useSelector((state) => state.search.open);

  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const notificationsRef = useRef(null);
  const profileRef = useRef(null);
  const searchRef = useRef(null);

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
    dispatch(fetchUnreadCount());
    dispatch(fetchNotifications({ page: 1, limit: 10 }));
  }, [dispatch]);

  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(fetchUnreadCount());
      dispatch(fetchNotifications({ page: 1, limit: 10 }));
    }, 60000);

    return () => clearInterval(interval);
  }, [dispatch]);

  useEffect(() => {
    const trimmed = searchQuery.trim();

    if (!trimmed) {
      dispatch(clearSearch());
      return;
    }

    const timer = setTimeout(() => {
      dispatch(
        fetchSearchResults({
          query: trimmed,
          projectId: selectedProjectId || undefined,
        })
      );
    }, 350);

    return () => clearTimeout(timer);
  }, [dispatch, searchQuery, selectedProjectId]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        profileOpen &&
        profileRef.current &&
        !profileRef.current.contains(event.target)
      ) {
        setProfileOpen(false);
      }

      if (
        notificationsOpen &&
        notificationsRef.current &&
        !notificationsRef.current.contains(event.target)
      ) {
        setNotificationsOpen(false);
      }

      if (
        searchOpen &&
        searchRef.current &&
        !searchRef.current.contains(event.target)
      ) {
        dispatch(closeSearch());
      }
    };

    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setProfileOpen(false);
        setNotificationsOpen(false);
        dispatch(closeSearch());
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [profileOpen, notificationsOpen, searchOpen, dispatch]);

  const formatNotificationTime = (value) => {
    if (!value) return "Recently";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Recently";

    const diffMs = Date.now() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  const handleLogout = () => {
    logoutUser();
    setProfileOpen(false);
    navigate("/", { replace: true });
  };

  const handleSettingsClick = () => {
    setProfileOpen(false);
    navigate("/app/settings");
  };

  const handleNotificationToggle = () => {
    const nextOpen = !notificationsOpen;
    setNotificationsOpen(nextOpen);

    if (nextOpen) {
      dispatch(fetchUnreadCount());
      dispatch(
        fetchNotifications({
          page: 1,
          limit: 10,
          source: "dropdown",
        })
      );
    }
  };

  const handleNotificationClick = async (notification) => {
    if (notification.status === "UNREAD") {
      await dispatch(markNotificationRead(notification.id));
      dispatch(fetchUnreadCount());
    }

    setNotificationsOpen(false);

    if (notification.entityType === "report") {
      navigate("/app/reports");
      return;
    }

    if (notification.entityType === "audit") {
      navigate("/app/audit");
      return;
    }

    if (notification.entityType === "keyword") {
      navigate("/app/keywords");
      return;
    }

    if (notification.projectId) {
      navigate("/app/projects");
    }
  };

  const handleMarkAllRead = async () => {
    await dispatch(markAllNotificationsRead());
    dispatch(fetchUnreadCount());

    if (notificationsOpen) {
      dispatch(
        fetchNotifications({
          page: 1,
          limit: 10,
          source: "dropdown",
        })
      );
    }
  };

  const handleViewAllNotifications = () => {
    setNotificationsOpen(false);
    navigate("/app/notifications");
  };

  const handleSearchNavigate = (type, item) => {
    const targetProjectId =
      type === "project" ? item.id : item.project?.id || null;

    if (targetProjectId) {
      dispatch(setSelectedProjectId(targetProjectId));
    }

    dispatch(closeSearch());
    dispatch(setSearchQuery(""));

    if (type === "project") {
      navigate("/app/projects");
      return;
    }

    if (type === "keyword") {
      navigate("/app/keywords");
      return;
    }

    if (type === "report") {
      navigate("/app/reports");
      return;
    }

    navigate("/app/projects");
  };

  const totalResults =
    (searchResults?.totals?.projects || 0) +
    (searchResults?.totals?.keywords || 0) +
    (searchResults?.totals?.reports || 0);

  return (
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

        <div
          ref={searchRef}
          className="relative hidden max-w-xl flex-1 md:block"
        >
          <div className="flex items-center rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <FontAwesomeIcon icon={faSearch} className="mr-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => dispatch(setSearchQuery(e.target.value))}
              onFocus={() => {
                if (searchQuery.trim()) {
                  dispatch(fetchSearchResults({
                    query: searchQuery.trim(),
                    projectId: selectedProjectId || undefined,
                  }));
                }
              }}
              placeholder="Search keywords, pages, reports..."
              className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
            />
          </div>

          {searchOpen && searchQuery.trim() && (
            <div className="absolute left-0 right-0 mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">
                  Search results
                </p>
                <p className="text-xs text-slate-500">
                  {searchLoading
                    ? "Searching..."
                    : `${totalResults} result${totalResults === 1 ? "" : "s"} found`}
                </p>
              </div>

              <div className="max-h-[420px] overflow-y-auto">
                {searchLoading ? (
                  <div className="px-4 py-6 text-sm text-slate-500">
                    Searching...
                  </div>
                ) : searchError ? (
                  <div className="px-4 py-6 text-sm text-rose-500">
                    {searchError}
                  </div>
                ) : totalResults === 0 ? (
                  <div className="px-4 py-6 text-sm text-slate-500">
                    No results found.
                  </div>
                ) : (
                  <div className="py-2">
                    {searchResults.keywords?.length > 0 && (
                      <div>
                        <p className="px-4 py-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
                          Keywords
                        </p>
                        {searchResults.keywords.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => handleSearchNavigate("keyword", item)}
                            className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
                          >
                            <FontAwesomeIcon icon={faKey} className="mt-1 text-slate-400" />
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-slate-900">
                                {item.keyword}
                              </p>
                              <p className="truncate text-xs text-slate-500">
                                {item.project?.name} · {item.location || "All locations"} · {item.device || "all devices"}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {searchResults.projects?.length > 0 && (
                      <div>
                        <p className="px-4 py-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
                          Projects
                        </p>
                        {searchResults.projects.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => handleSearchNavigate("project", item)}
                            className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
                          >
                            <FontAwesomeIcon icon={faFolderOpen} className="mt-1 text-slate-400" />
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-slate-900">
                                {item.name}
                              </p>
                              <p className="truncate text-xs text-slate-500">
                                {item.domain || "No domain"}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {searchResults.reports?.length > 0 && (
                      <div>
                        <p className="px-4 py-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
                          Reports
                        </p>
                        {searchResults.reports.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => handleSearchNavigate("report", item)}
                            className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
                          >
                            <FontAwesomeIcon icon={faFileLines} className="mt-1 text-slate-400" />
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-slate-900">
                                {item.title}
                              </p>
                              <p className="truncate text-xs text-slate-500">
                                {item.project?.name} · {item.period} · {item.status}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
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

          <div className="relative" ref={notificationsRef}>
            <button
              type="button"
              onClick={handleNotificationToggle}
              className="relative inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600"
              aria-label="Open notifications"
              aria-expanded={notificationsOpen}
            >
              <FontAwesomeIcon icon={faBell} />
              {unreadCount > 0 && (
                <span className="absolute right-0.5 top-0.5 min-w-[18px] rounded-full bg-rose-500 px-1.5 text-[10px] font-bold leading-5 text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-3 w-[360px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      Notifications
                    </p>
                    <p className="text-xs text-slate-500">
                      {unreadCount} unread
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleMarkAllRead}
                    className="text-xs font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Mark all read
                  </button>
                </div>

                <div className="max-h-[420px] overflow-y-auto">
                  {notificationsLoading ? (
                    <div className="px-4 py-6 text-sm text-slate-500">
                      Loading notifications...
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="px-4 py-6 text-sm text-slate-500">
                      No notifications found.
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <button
                        key={notification.id}
                        type="button"
                        onClick={() => handleNotificationClick(notification)}
                        className={`flex w-full flex-col items-start gap-1 border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 ${notification.status === "UNREAD"
                            ? "bg-brand-50/40"
                            : "bg-white"
                          }`}
                      >
                        <div className="flex w-full items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-slate-900">
                            {notification.title}
                          </p>
                          {notification.status === "UNREAD" && (
                            <span className="mt-1 h-2.5 w-2.5 rounded-full bg-brand-600" />
                          )}
                        </div>

                        <p className="text-xs text-slate-600">
                          {notification.message}
                        </p>

                        <div className="flex w-full items-center justify-between gap-3">
                          {/* <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">
                            {notification.type.replaceAll("_", " ")}
                          </p> */}
                          <p className="text-[11px] text-slate-400">
                            {formatNotificationTime(notification.createdAt)}
                          </p>
                        </div>
                      </button>
                    ))
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleViewAllNotifications}
                  className="w-full border-t border-slate-100 px-4 py-3 text-sm font-semibold text-brand-600 transition hover:bg-slate-50"
                >
                  View all notifications
                </button>
              </div>
            )}
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
  );
}

export default Topbar;