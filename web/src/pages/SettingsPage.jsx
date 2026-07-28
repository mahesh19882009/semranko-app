import { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  clearSettingsMessages,
  fetchMySettings,
  updateNotifications,
  updatePassword,
  updateProfile,
} from "../features/settings/settingsSlice";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";

const SettingsPage = () => {
  const dispatch = useDispatch();

  const {
    settings,
    loading,
    profileLoading,
    notificationsLoading,
    passwordLoading,
    error,
    successMessage,
  } = useSelector((state) => state.settings);

  const [profileForm, setProfileForm] = useState({
    name: "",
    email: "",
  });

  const [notificationForm, setNotificationForm] = useState({
    dailyKeywordMovement: true,
    weeklyAuditSummary: true,
    competitorAlerts: false,
  });

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  useEffect(() => {
    dispatch(fetchMySettings());
  }, [dispatch]);

  useEffect(() => {
    if (!settings) return;

    setProfileForm({
      name: settings.name || "",
      email: settings.email || "",
    });

    setNotificationForm({
      dailyKeywordMovement: !!settings.dailyKeywordMovement,
      weeklyAuditSummary: !!settings.weeklyAuditSummary,
      competitorAlerts: !!settings.competitorAlerts,
    });
  }, [settings]);

  useEffect(() => {
    return () => {
      dispatch(clearSettingsMessages());
    };
  }, [dispatch]);

  const profileChanged = useMemo(() => {
    if (!settings) return false;
    return profileForm.name.trim() !== (settings.name || "").trim();
  }, [profileForm.name, settings]);

  const notificationsChanged = useMemo(() => {
    if (!settings) return false;

    return (
      notificationForm.dailyKeywordMovement !==
        !!settings.dailyKeywordMovement ||
      notificationForm.weeklyAuditSummary !== !!settings.weeklyAuditSummary ||
      notificationForm.competitorAlerts !== !!settings.competitorAlerts
    );
  }, [notificationForm, settings]);

  const passwordMismatch =
    passwordForm.confirmPassword &&
    passwordForm.newPassword !== passwordForm.confirmPassword;

  const handleProfileInputChange = (e) => {
    const { name, value } = e.target;
    setProfileForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleNotificationChange = (e) => {
    const { name, checked } = e.target;
    setNotificationForm((prev) => ({
      ...prev,
      [name]: checked,
    }));
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    dispatch(clearSettingsMessages());
    await dispatch(
      updateProfile({
        name: profileForm.name.trim(),
      })
    );
  };

  const handleNotificationsSubmit = async (e) => {
    e.preventDefault();
    dispatch(clearSettingsMessages());
    await dispatch(updateNotifications(notificationForm));
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    dispatch(clearSettingsMessages());

    if (passwordMismatch) return;

    const result = await dispatch(updatePassword(passwordForm));

    if (updatePassword.fulfilled.match(result)) {
      setPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <Alert
          variant="plain"
          message="Loading settings..."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your profile, notifications and password.
        </p>
      </div>

      {error ? (
        <Alert
          variant="error"
          message={error}
        />
      ) : null}

      {successMessage ? (
        <Alert
          variant="success"
          message={successMessage}
        />
      ) : null}

      <div className="grid gap-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">Profile</h2>
            <p className="mt-1 text-sm text-slate-500">
              Update your account information. Email is locked and cannot be changed.
            </p>
          </div>

          <form onSubmit={handleProfileSubmit} className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium text-slate-700">
                Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                value={profileForm.name}
                onChange={handleProfileInputChange}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400"
                placeholder="Enter your name"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-slate-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={profileForm.email}
                disabled
                className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-100 px-4 py-3 text-sm text-slate-500 outline-none"
                placeholder="Email"
              />
              <p className="text-xs text-slate-500">Email cannot be changed.</p>
            </div>

            <div className="md:col-span-2 flex justify-end">
              <Button
                type="submit"
                disabled={profileLoading || !profileChanged}
                loading={profileLoading}
              >
                Save profile
              </Button>
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">Notifications</h2>
            <p className="mt-1 text-sm text-slate-500">
              Choose which notifications you want to receive.
            </p>
          </div>

          <form onSubmit={handleNotificationsSubmit} className="space-y-4">
            <label className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-4">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  Daily keyword movement
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Get daily updates for keyword ranking changes.
                </p>
              </div>
              <input
                type="checkbox"
                name="dailyKeywordMovement"
                checked={notificationForm.dailyKeywordMovement}
                onChange={handleNotificationChange}
                className="h-4 w-4"
              />
            </label>

            <label className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-4">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  Weekly audit summary
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Receive a weekly SEO audit summary.
                </p>
              </div>
              <input
                type="checkbox"
                name="weeklyAuditSummary"
                checked={notificationForm.weeklyAuditSummary}
                onChange={handleNotificationChange}
                className="h-4 w-4"
              />
            </label>

            <label className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-4">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  Competitor alerts
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Get notified when competitors make major ranking gains.
                </p>
              </div>
              <input
                type="checkbox"
                name="competitorAlerts"
                checked={notificationForm.competitorAlerts}
                onChange={handleNotificationChange}
                className="h-4 w-4"
              />
            </label>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={notificationsLoading || !notificationsChanged}
                loading={notificationsLoading}
              >
                Save notifications
              </Button>
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">Password</h2>
            <p className="mt-1 text-sm text-slate-500">
              Change your password securely.
            </p>
          </div>

          <form onSubmit={handlePasswordSubmit} className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label
                htmlFor="currentPassword"
                className="text-sm font-medium text-slate-700"
              >
                Current password
              </label>
              <input
                id="currentPassword"
                name="currentPassword"
                type="password"
                autoComplete="current-password"
                value={passwordForm.currentPassword}
                onChange={handlePasswordInputChange}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400"
                placeholder="Current password"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="newPassword"
                className="text-sm font-medium text-slate-700"
              >
                New password
              </label>
              <input
                id="newPassword"
                name="newPassword"
                type="password"
                autoComplete="new-password"
                value={passwordForm.newPassword}
                onChange={handlePasswordInputChange}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400"
                placeholder="New password"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="confirmPassword"
                className="text-sm font-medium text-slate-700"
              >
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={passwordForm.confirmPassword}
                onChange={handlePasswordInputChange}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400"
                placeholder="Confirm new password"
              />
            </div>

            {passwordMismatch ? (
              <div className="md:col-span-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                New password and confirm password do not match.
              </div>
            ) : null}

            <div className="md:col-span-3 flex justify-end">
              <Button
                type="submit"
                disabled={
                  passwordLoading ||
                  !passwordForm.currentPassword ||
                  !passwordForm.newPassword ||
                  !passwordForm.confirmPassword ||
                  passwordMismatch
                }
                loading={passwordLoading}
              >
                Update password
              </Button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
};

export default SettingsPage;