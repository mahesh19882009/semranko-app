import { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  deleteNotification,
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../features/notifications/notificationsSlice";
import { useNavigate } from "react-router-dom";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";

function NotificationsPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const project = useSelector(selectSelectedProject);

  const { items, loading, actionLoading, unreadCount, pagination } = useSelector(
    (state) => state.notifications,
  );

  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    dispatch(
      fetchNotifications({
        page,
        limit: 10,
        status: statusFilter,
      }),
    );
    dispatch(fetchUnreadCount());
  }, [dispatch, page, statusFilter, project?.id]);

  const formatNotificationTime = (value) => {
    if (!value) return "Recently";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Recently";

    const diffMs = Date.now() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours} hours ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleString();
  };

  const filteredLabel = useMemo(() => {
    if (statusFilter === "unread") return "Unread notifications";
    if (statusFilter === "read") return "Read notifications";
    return "All notifications";
  }, [statusFilter]);

  const handleOpenNotification = async (notification) => {
    if (notification.status === "UNREAD") {
      await dispatch(markNotificationRead(notification.id));
      dispatch(fetchUnreadCount());
    }

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
      navigate("/app");
    }
  };

  const handleMarkAllRead = async () => {
    await dispatch(markAllNotificationsRead());
    dispatch(fetchUnreadCount());
    dispatch(
      fetchNotifications({
        page,
        limit: 10,
        status: statusFilter,
      }),
    );
  };

  const handleDelete = async (notificationId) => {
    await dispatch(deleteNotification(notificationId));
    dispatch(fetchUnreadCount());
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track alerts for reports, audits, keyword changes, and system updates.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 outline-none"
          >
            <option value="all">All</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>

          <button
            type="button"
            onClick={handleMarkAllRead}
            disabled={actionLoading || unreadCount === 0}
            className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Mark all read
          </button>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <p className="text-sm font-semibold text-slate-900">{filteredLabel}</p>
            <p className="text-xs text-slate-500">{unreadCount} unread total</p>
          </div>
        </div>

        {loading ? (
          <div className="px-6 py-10 text-sm text-slate-500">
            Loading notifications...
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-10 text-sm text-slate-500">
            No notifications found.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((notification) => (
              <div
                key={notification.id}
                className={`flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-start lg:justify-between ${
                  notification.status === "UNREAD" ? "bg-brand-50/30" : "bg-white"
                }`}
              >
                <button
                  type="button"
                  onClick={() => handleOpenNotification(notification)}
                  className="flex-1 text-left"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-1 h-2.5 w-2.5 rounded-full ${
                        notification.status === "UNREAD"
                          ? "bg-brand-600"
                          : "bg-slate-300"
                      }`}
                    />
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">
                          {notification.title}
                        </p>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                          {notification.type.replaceAll("_", " ")}
                        </span>
                      </div>

                      <p className="text-sm text-slate-600">
                        {notification.message}
                      </p>

                      <p className="text-xs text-slate-400">
                        {formatNotificationTime(notification.createdAt)}
                      </p>
                    </div>
                  </div>
                </button>

                <div className="flex items-center gap-3">
                  {notification.status === "UNREAD" && (
                    <button
                      type="button"
                      onClick={() => handleOpenNotification(notification)}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      Mark read
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleDelete(notification.id)}
                    className="rounded-xl border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-600 transition hover:bg-rose-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-slate-100 px-6 py-4">
          <p className="text-xs text-slate-500">
            Page {pagination.page} of {pagination.totalPages || 1}
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>

            <button
              type="button"
              disabled={pagination.totalPages ? page >= pagination.totalPages : true}
              onClick={() => setPage((prev) => prev + 1)}
              className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default NotificationsPage;