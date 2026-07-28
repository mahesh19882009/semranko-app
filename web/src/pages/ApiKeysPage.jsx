import { useState, useEffect } from "react";
import { createApiKeyApi, listApiKeysApi, deactivateApiKeyApi, deleteApiKeyApi } from "../lib/api";
import { formatDate } from "../utils/date";

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyExpiry, setNewKeyExpiry] = useState("");
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await listApiKeysApi();
      setApiKeys(result.data.keys || []);
    } catch (err) {
      setError(err?.message || "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    setCreating(true);
    setError("");

    try {
      const result = await createApiKeyApi(
        newKeyName,
        newKeyExpiry ? parseInt(newKeyExpiry) : null
      );
      
      setCreatedKey(result.data);
      setShowCreateModal(false);
      setNewKeyName("");
      setNewKeyExpiry("");
      await loadApiKeys();
    } catch (err) {
      setError(err?.message || "Failed to create API key");
    } finally {
      setCreating(false);
    }
  };

  const handleDeactivate = async (apiKeyId) => {
    if (!confirm("Are you sure you want to deactivate this API key?")) return;

    try {
      await deactivateApiKeyApi(apiKeyId);
      await loadApiKeys();
    } catch (err) {
      setError(err?.message || "Failed to deactivate API key");
    }
  };

  const handleDelete = async (apiKeyId) => {
    if (!confirm("Are you sure you want to delete this API key? This action cannot be undone.")) return;

    try {
      await deleteApiKeyApi(apiKeyId);
      await loadApiKeys();
    } catch (err) {
      setError(err?.message || "Failed to delete API key");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">API Keys</h1>
            <p className="text-slate-600">Manage your API keys for programmatic access</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700"
          >
            Create API Key
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {createdKey && (
          <div className="mb-6 p-6 bg-green-50 border border-green-200 rounded-lg">
            <h3 className="text-lg font-semibold text-green-900 mb-2">API Key Created Successfully!</h3>
            <p className="text-sm text-green-700 mb-4">Copy this key now. You won't be able to see it again.</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={createdKey.key}
                readOnly
                className="flex-1 px-4 py-2 border border-green-300 rounded-lg bg-white font-mono text-sm"
              />
              <button
                onClick={() => copyToClipboard(createdKey.key)}
                className="bg-green-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-green-700"
              >
                Copy
              </button>
              <button
                onClick={() => setCreatedKey(null)}
                className="bg-slate-200 text-slate-700 py-2 px-4 rounded-lg font-medium hover:bg-slate-300"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          {loading ? (
            <div className="text-center py-8">
              <p className="text-slate-600">Loading API keys...</p>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-slate-600">No API keys found.</p>
              <p className="text-sm text-slate-500 mt-1">Create your first API key to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Name</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Key</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Last Used</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Expires</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr key={key.id} className="border-b border-slate-100">
                      <td className="py-3 px-4 text-sm font-medium text-slate-900">{key.name}</td>
                      <td className="py-3 px-4 text-sm text-slate-600 font-mono">{key.key}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          key.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {key.isActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {formatDate(key.lastUsed)}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {formatDate(key.expiresAt)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          {key.isActive && (
                            <button
                              onClick={() => handleDeactivate(key.id)}
                              className="text-sm text-slate-600 hover:text-slate-900"
                            >
                              Deactivate
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(key.id)}
                            className="text-sm text-red-600 hover:text-red-900"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Create API Key</h2>
              
              <form onSubmit={handleCreateKey}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Name
                  </label>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g., Production App"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Expires in days (optional)
                  </label>
                  <input
                    type="number"
                    value={newKeyExpiry}
                    onChange={(e) => setNewKeyExpiry(e.target.value)}
                    placeholder="e.g., 30"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="1"
                  />
                  <p className="text-xs text-slate-500 mt-1">Leave empty for no expiration</p>
                </div>

                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {creating ? "Creating..." : "Create"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
