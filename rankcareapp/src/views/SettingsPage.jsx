'use client'
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { useDispatch, useSelector } from "react-redux";
import {
  fetchSettingsProfile,
  updateSettingsProfile,
  fetchGstInfo,
  updateGstInfo,
  changeSettingsPassword,
} from "../features/settings/settingsSlice";
import { ToastProvider, useToast } from "../components/ui/Toast";
import Card from "../components/ui/Card";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";
import { formatDate } from "../utils/date";

function SettingsContent() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();
  const dispatch = useDispatch();
  const initialized = useRef(false);

  const profile = useSelector((state) => state.settings.profile);
  const gstInfo = useSelector((state) => state.settings.gstInfo);

  const loadingProfile = useSelector((state) => state.settings.loadingProfile);
  const loadingGst = useSelector((state) => state.settings.loadingGst);
  const changingPassword = useSelector((state) => state.settings.changingPassword);
  const updatingProfile = useSelector((state) => state.settings.updatingProfile);
  const updatingGst = useSelector((state) => state.settings.updatingGst);

  const error = useSelector((state) => state.settings.error);

  const [name, setName] = useState("");
  const [nameError, setNameError] = useState("");
  const [profileSaved, setProfileSaved] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const [gstin, setGstin] = useState("");
  const [gstName, setGstName] = useState("");
  const [gstAddress, setGstAddress] = useState("");
  const [gstState, setGstState] = useState("");
  const [gstStateCode, setGstStateCode] = useState("");
  const [gstError, setGstError] = useState("");
  const [gstSaved, setGstSaved] = useState(false);

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    if (initialized.current) return;
    initialized.current = true;
    dispatch(fetchSettingsProfile());
    dispatch(fetchGstInfo());
  }, [authenticated, navigate, dispatch]);

  useEffect(() => {
    if (profile) {
      setName(profile.name || "");
    }
  }, [profile]);

  useEffect(() => {
    if (gstInfo) {
      setGstin(gstInfo.gstin || "");
      setGstName(gstInfo.gstName || "");
      setGstAddress(gstInfo.gstAddress || "");
      setGstState(gstInfo.gstState || "");
      setGstStateCode(gstInfo.gstStateCode || "");
    }
  }, [gstInfo]);

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setNameError("");
    setProfileSaved(false);

    const trimmed = name.trim();
    if (trimmed.length < 2 || trimmed.length > 100) {
      setNameError("Name must be between 2 and 100 characters");
      return;
    }

    try {
      const result = await dispatch(updateSettingsProfile({ name: trimmed })).unwrap();
      setProfileSaved(true);
      addToast("Profile updated successfully", "success");
    } catch (err) {
      setNameError(err || "Failed to update profile");
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess(false);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("All fields are required");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    if (profile?.authProvider && profile.authProvider !== "local") {
      setPasswordError("Password change is only available for local accounts");
      return;
    }

    try {
      const result = await dispatch(
        changeSettingsPassword({ currentPassword, newPassword })
      ).unwrap();
      setPasswordSuccess(true);
      addToast("Password changed successfully", "success");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(err || "Failed to change password");
    }
  };

  const handleGstSubmit = async (e) => {
    e.preventDefault();
    setGstError("");
    setGstSaved(false);

    const trimmedGstin = gstin.trim();
    if (trimmedGstin && !/^[A-Z0-9]{15}$/.test(trimmedGstin)) {
      setGstError("GSTIN must be 15 alphanumeric characters (uppercase)");
      return;
    }

    try {
      await dispatch(
        updateGstInfo({
          gstin: trimmedGstin || null,
          gstName: gstName.trim() || null,
          gstAddress: gstAddress.trim() || null,
          gstState: gstState.trim() || null,
          gstStateCode: gstStateCode.trim() || null,
        })
      ).unwrap();
      setGstSaved(true);
      addToast("GST information updated successfully", "success");
    } catch (err) {
      setGstError(err || "Failed to update GST information");
    }
  };

  const planLabel = profile?.selectedPlan || "—";
  const planStatus = profile?.subscriptionStatus || "—";

  if (!authenticated) {
    return null;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
        <p className="mt-2 text-sm text-slate-500">
          Manage your account, security, and billing information.
        </p>
      </div>

      {error && (
        <Alert variant="error" message={error} onDismiss={() => dispatch({ type: "settings/clearSettingsError" })} />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card className="!p-0">
            <div className="border-b border-slate-200 px-6 py-5">
              <h2 className="text-lg font-semibold text-slate-900">Profile Information</h2>
              <p className="mt-1 text-sm text-slate-500">Update your personal details and view plan information.</p>
            </div>
            <form onSubmit={handleProfileSubmit} className="p-6 space-y-5">
              <Input
                label="Display Name"
                name="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                error={nameError}
                placeholder="Your name"
              />
              <Input
                label="Email"
                name="email"
                value={profile?.email || ""}
                disabled
                hint="Email is used for login and cannot be changed here."
              />
              <div className="grid items-center gap-3 grid-cols-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-500">Plan</p>
                  <p className="text-sm font-semibold text-slate-900 capitalize">{planLabel}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-500">Status</p>
                  <p className="text-sm font-semibold text-slate-900 capitalize">{planStatus}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-500">Credits</p>
                  <p className="text-sm font-semibold text-slate-900">
                    {profile?.creditBalance !== null && profile?.creditBalance !== undefined
                      ? profile.creditBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      : "—"}
                  </p>
                </div>
              </div>
              {profile?.subscriptionStatus === "active" && profile?.subscriptionEndDate ? (
                <p className="text-xs text-slate-500">
                  Plan ends: {formatDate(profile.subscriptionEndDate)}
                </p>
              ) : profile?.trialEndsAt ? (
                <p className="text-xs text-slate-500">
                  Trial ends: {formatDate(profile.trialEndsAt)}
                </p>
              ) : null}
              <div className="flex items-center gap-3">
                <Button type="submit" loading={updatingProfile}>
                  Save Profile
                </Button>
                {profileSaved && (
                  <span className="text-sm text-emerald-600">Saved</span>
                )}
              </div>
            </form>
          </Card>

          <Card className="!p-0">
            <div className="border-b border-slate-200 px-6 py-5">
              <h2 className="text-lg font-semibold text-slate-900">Billing & GST Information</h2>
              <p className="mt-1 text-sm text-slate-500">Your GST details are used for invoicing.</p>
            </div>
            <form onSubmit={handleGstSubmit} className="p-6 space-y-5">
              <div className="grid gap-5 sm:grid-cols-2">
                <Input
                  label="GSTIN"
                  name="gstin"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="e.g. 06FHDPK2516L1ZB"
                  maxLength={15}
                  hint="15 alphanumeric characters (optional)"
                />
                <Input
                  label="Business Name"
                  name="gstName"
                  value={gstName}
                  onChange={(e) => setGstName(e.target.value)}
                  placeholder="Legal business name"
                />
              </div>
              <Input
                label="Business Address"
                name="gstAddress"
                value={gstAddress}
                onChange={(e) => setGstAddress(e.target.value)}
                placeholder="Full address"
              />
              <div className="grid gap-5 sm:grid-cols-2">
                <Input
                  label="State"
                  name="gstState"
                  value={gstState}
                  onChange={(e) => setGstState(e.target.value)}
                  placeholder="e.g. Haryana"
                />
                <Input
                  label="State Code"
                  name="gstStateCode"
                  value={gstStateCode}
                  onChange={(e) => setGstStateCode(e.target.value)}
                  placeholder="e.g. 06"
                  maxLength={2}
                />
              </div>
              {gstError && (
                <Alert variant="error" message={gstError} onDismiss={() => setGstError("")} />
              )}
              {gstSaved && (
                <Alert variant="success" message="GST information updated" onDismiss={() => setGstSaved(false)} />
              )}
              <Button type="submit" loading={updatingGst}>
                Save GST Info
              </Button>
            </form>
          </Card>
        </div>
        <div>
          <Card className="!p-0">
            <div className="border-b border-slate-200 px-6 py-5">
              <h2 className="text-lg font-semibold text-slate-900">Change Password</h2>
              <p className="mt-1 text-sm text-slate-500">Update your password. You must know your current password.</p>
            </div>
            <form onSubmit={handlePasswordSubmit} className="p-6 space-y-5">
              {(profile?.authProvider && profile.authProvider !== "local") && (
                <Alert variant="warning" message="Password management is not available for accounts created with Google." />
              )}
              <Input
                label="Current Password"
                name="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
              <Input
                label="New Password"
                name="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
              <Input
                label="Confirm New Password"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
              {passwordError && (
                <Alert variant="error" message={passwordError} onDismiss={() => setPasswordError("")} />
              )}
              <Button type="submit" loading={changingPassword} disabled={profile?.authProvider && profile.authProvider !== "local"}>
                Change Password
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
    }
  }, [authenticated, navigate]);

  if (!authenticated) {
    return null;
  }

  return (
    <ToastProvider>
      <SettingsContent />
    </ToastProvider>
  );
}
