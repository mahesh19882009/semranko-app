import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import {
  createScheduledReportApi,
  listScheduledReportsApi,
  updateScheduledReportApi,
  deleteScheduledReportApi,
} from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import { formatDate } from "../utils/date";
import ConfirmModal from "../components/ConfirmModal";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

export default function ScheduledReportsPage() {
  const selectedProject = useSelector(selectSelectedProject);
  
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    frequency: "weekly",
    format: "pdf",
    recipients: "",
    startDate: "",
  });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [createError, setCreateError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [reportToDelete, setReportToDelete] = useState(null);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await listScheduledReportsApi();
      setReports(result.data.reports || []);
    } catch (err) {
      setError(err?.message || "Failed to load scheduled reports");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!selectedProject?.id || !formData.name.trim() || !formData.recipients.trim()) return;

    setCreateError("");

    // Validate max 2 recipients
    const recipientList = formData.recipients.split(',').map(r => r.trim()).filter(r => r);
    if (recipientList.length > 2) {
      setCreateError("Maximum of 2 recipients allowed");
      return;
    }

    setCreating(true);

    try {
      await createScheduledReportApi(
        selectedProject.id,
        formData.name,
        formData.frequency,
        formData.format,
        formData.recipients,
        formData.startDate
      );
      
      setShowCreateModal(false);
      setFormData({ name: "", frequency: "weekly", format: "pdf", recipients: "", startDate: "" });
      await loadReports();
    } catch (err) {
      if (err?.message === "Maximum of 2 scheduled reports allowed per project" ||
          err?.message === "Maximum of 2 recipients allowed per scheduled report") {
        setCreateError(err.message);
      } else {
        setError(err?.message || "Failed to create scheduled report");
      }
    } finally {
      setCreating(false);
    }
  };

  const handleToggleActive = async (reportId, isActive) => {
    try {
      await updateScheduledReportApi(reportId, { is_active: !isActive });
      await loadReports();
    } catch (err) {
      setError(err?.message || "Failed to update scheduled report");
    }
  };

  const handleDelete = (reportId, reportName) => {
    setReportToDelete({ id: reportId, name: reportName });
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!reportToDelete?.id) return;

    try {
      await deleteScheduledReportApi(reportToDelete.id);
      setShowDeleteConfirm(false);
      setReportToDelete(null);
      await loadReports();
    } catch (err) {
      setError(err?.message || "Failed to delete scheduled report");
      setShowDeleteConfirm(false);
      setReportToDelete(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Scheduled Reports</h1>
            <p className="text-slate-600">Automate your SEO reporting with scheduled email reports</p>
          </div>
          <Button
            onClick={() => {
              setCreateError("");
              setShowCreateModal(true);
            }}
            disabled={!selectedProject?.id}
          >
            Create Scheduled Report
          </Button>
        </div>

        {!selectedProject?.id && (
          <Alert variant="warning" message="Please select a project to create scheduled reports" />
        )}

        {error && (
          <Alert variant="error" message={error} />
        )}

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          {loading ? (
            <div className="text-center py-8">
              <p className="text-slate-600">Loading scheduled reports...</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-slate-600">No scheduled reports found.</p>
              <p className="text-sm text-slate-500 mt-1">Create your first scheduled report to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200 sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                      <th className="text-left py-3 px-4 font-medium">Name</th>
                      <th className="text-left py-3 px-4 font-medium">Frequency</th>
                      <th className="text-left py-3 px-4 font-medium">Format</th>
                      <th className="text-left py-3 px-4 font-medium">Recipients</th>
                      <th className="text-left py-3 px-4 font-medium">Next Send</th>
                      <th className="text-left py-3 px-4 font-medium">Status</th>
                      <th className="text-left py-3 px-4 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((report) => (
                      <tr key={report.id} className="border-b border-slate-100">
                        <td className="py-3 px-4 text-sm font-medium text-slate-900">{report.name}</td>
                        <td className="py-3 px-4 text-sm text-slate-600 capitalize">{report.frequency}</td>
                        <td className="py-3 px-4 text-sm text-slate-600 uppercase">{report.format}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">{report.recipients}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">
                          {formatDate(report.nextSendAt)}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            report.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {report.isActive ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleToggleActive(report.id, report.isActive)}
                            >
                              {report.isActive ? 'Pause' : 'Activate'}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDelete(report.id, report.name)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Create Scheduled Report</h2>
              
              <form onSubmit={handleCreate}>
                {createError && (
                  <Alert variant="error" message={createError} />
                )}
                
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Report Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="e.g., Weekly SEO Report"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Frequency
                  </label>
                  <select
                    value={formData.frequency}
                    onChange={(e) => setFormData({...formData, frequency: e.target.value})}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Format
                  </label>
                  <select
                    value={formData.format}
                    onChange={(e) => setFormData({...formData, format: e.target.value})}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="pdf">PDF</option>
                    <option value="csv">CSV</option>
                  </select>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Recipients (comma-separated emails, max 2)
                  </label>
                  <input
                    type="text"
                    value={formData.recipients}
                    onChange={(e) => setFormData({...formData, recipients: e.target.value})}
                    placeholder="e.g., john@example.com, jane@example.com"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Start Date (optional)
                  </label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => setFormData({...formData, startDate: e.target.value})}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex gap-2 justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setCreateError("");
                      setShowCreateModal(false);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={creating}
                    loading={creating}
                  >
                    Create
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        title="Delete Scheduled Report"
        message={`Are you sure you want to delete "${reportToDelete?.name || 'this scheduled report'}"?`}
      />
    </div>
  );
}
