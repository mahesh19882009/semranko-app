import { useState, useEffect } from "react";
import {
  getWhiteLabelSettingsApi,
  updateWhiteLabelSettingsApi,
  deleteWhiteLabelSettingsApi,
} from "../lib/api";
import ConfirmModal from "../components/ConfirmModal";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

export default function WhiteLabelPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [formData, setFormData] = useState({
    companyName: "",
    logoUrl: "",
    primaryColor: "#000000",
    secondaryColor: "#ffffff",
    customDomain: "",
    hideBranding: false,
  });
  const [error, setError] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await getWhiteLabelSettingsApi();
      if (result.data.settings) {
        setSettings(result.data.settings);
        setFormData({
          companyName: result.data.settings.companyName || "",
          logoUrl: result.data.settings.logoUrl || "",
          primaryColor: result.data.settings.primaryColor || "#000000",
          secondaryColor: result.data.settings.secondaryColor || "#ffffff",
          customDomain: result.data.settings.customDomain || "",
          hideBranding: result.data.settings.hideBranding || false,
        });
      }
    } catch (err) {
      setError(err?.message || "Failed to load white label settings");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      const result = await updateWhiteLabelSettingsApi(formData);
      setSettings(result.data);
    } catch (err) {
      setError(err?.message || "Failed to save white label settings");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setShowResetConfirm(true);
  };

  const confirmReset = async () => {
    setShowResetConfirm(false);
    
    try {
      await deleteWhiteLabelSettingsApi();
      setSettings(null);
      setFormData({
        companyName: "",
        logoUrl: "",
        primaryColor: "#000000",
        secondaryColor: "#ffffff",
        customDomain: "",
        hideBranding: false,
      });
    } catch (err) {
      setError(err?.message || "Failed to delete white label settings");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">White Label Settings</h1>
          <p className="text-slate-600">Customize your reports with your own branding</p>
        </div>

        {error && (
          <Alert variant="error" message={error} />
        )}

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          {loading ? (
            <div className="text-center py-8">
              <p className="text-slate-600">Loading settings...</p>
            </div>
          ) : (
            <form onSubmit={handleSave}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={formData.companyName}
                    onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                    placeholder="Your Company Name"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Logo URL
                  </label>
                  <input
                    type="url"
                    value={formData.logoUrl}
                    onChange={(e) => setFormData({...formData, logoUrl: e.target.value})}
                    placeholder="https://example.com/logo.png"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Primary Color
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={formData.primaryColor}
                      onChange={(e) => setFormData({...formData, primaryColor: e.target.value})}
                      className="w-12 h-12 border border-slate-300 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={formData.primaryColor}
                      onChange={(e) => setFormData({...formData, primaryColor: e.target.value})}
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Secondary Color
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={formData.secondaryColor}
                      onChange={(e) => setFormData({...formData, secondaryColor: e.target.value})}
                      className="w-12 h-12 border border-slate-300 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={formData.secondaryColor}
                      onChange={(e) => setFormData({...formData, secondaryColor: e.target.value})}
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Custom Domain (optional)
                  </label>
                  <input
                    type="text"
                    value={formData.customDomain}
                    onChange={(e) => setFormData({...formData, customDomain: e.target.value})}
                    placeholder="reports.yourcompany.com"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">Requires DNS configuration</p>
                </div>

                <div className="md:col-span-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.hideBranding}
                      onChange={(e) => setFormData({...formData, hideBranding: e.target.checked})}
                      className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-slate-700">Hide RankCare branding</span>
                  </label>
                  <p className="text-xs text-slate-500 mt-1 ml-6">Remove RankCare logo and references from reports</p>
                </div>
              </div>

              {/* Preview */}
              {formData.companyName && (
                <div className="mt-6 p-4 border border-slate-200 rounded-lg">
                  <p className="text-sm font-medium text-slate-700 mb-3">Preview</p>
                  <div
                    className="p-4 rounded-lg"
                    style={{
                      backgroundColor: formData.primaryColor,
                      color: formData.secondaryColor,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      {formData.logoUrl && (
                        <img
                          src={formData.logoUrl}
                          alt="Logo"
                          className="w-10 h-10 object-contain"
                          onError={(e) => e.target.style.display = 'none'}
                        />
                      )}
                      <div>
                        <p className="font-bold">{formData.companyName}</p>
                        {!formData.hideBranding && (
                          <p className="text-xs opacity-70">Powered by RankCare</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-6 flex gap-3 justify-between">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleDelete}
                  disabled={!settings}
                  className="text-red-600 hover:text-red-700 border-red-300 hover:bg-red-50"
                >
                  Reset to Default
                </Button>
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    disabled={saving}
                    loading={saving}
                  >
                    Save Settings
                  </Button>
                </div>
              </div>
            </form>
          )}
        </div>

        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">White Label Features</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Custom company name and logo on reports</li>
            <li>• Custom color scheme</li>
            <li>• Optional custom domain for reports</li>
            <li>• Remove RankCare branding</li>
          </ul>
        </div>
      </div>

      <ConfirmModal
        isOpen={showResetConfirm}
        onClose={() => setShowResetConfirm(false)}
        onConfirm={confirmReset}
        title="Reset to Default"
        message="Are you sure you want to reset your white label settings to default? This action cannot be undone."
      />
    </div>
  );
}
