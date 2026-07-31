import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { getAioDashboardApi, getAioCitationsApi, trackAioApi } from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

export default function AIODashboardPage() {
  const selectedProject = useSelector(selectSelectedProject);

  const [dashboard, setDashboard] = useState(null);
  const [citations, setCitations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    if (!selectedProject?.id) return;
    setLoading(true);
    setError("");

    try {
      const result = await getAioDashboardApi(selectedProject.id);
      setDashboard(result.data);
    } catch (err) {
      setError(err?.message || "Failed to load AIO dashboard");
    } finally {
      setLoading(false);
    }
  };

  const loadCitations = async () => {
    if (!selectedProject?.id) return;
    setLoading(true);

    try {
      const result = await getAioCitationsApi(selectedProject.id);
      setCitations(result.data?.citations || []);
    } catch (err) {
      setError(err?.message || "Failed to load citations");
    } finally {
      setLoading(false);
    }
  };

  const handleTrack = async () => {
    if (!selectedProject?.id) return;
    setTracking(true);
    setError("");

    try {
      await trackAioApi(selectedProject.id);
      await loadDashboard();
      await loadCitations();
    } catch (err) {
      setError(err?.message || "Failed to track AIO");
    } finally {
      setTracking(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    loadCitations();
  }, [selectedProject?.id]);

  if (!selectedProject?.id) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">AIO Dashboard</h1>
          <p className="text-slate-600">Select a project to view AI Overview data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">AIO Dashboard</h1>
            <p className="text-slate-600">Track AI Overview presence and citation share of voice</p>
          </div>
          <Button onClick={handleTrack} loading={tracking} variant="primary">
            Refresh AIO Data
          </Button>
        </div>

        {error && <Alert variant="error" message={error} />}

        {dashboard && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Tracked Keywords</p>
              <p className="text-3xl font-bold text-slate-900">{dashboard.totalKeywords ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">With AI Overview</p>
              <p className="text-3xl font-bold text-blue-600">{dashboard.withAIOverview ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Without AI Overview</p>
              <p className="text-3xl font-bold text-slate-900">{dashboard.withoutAIOverview ?? 0}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">AIO Keywords</h2>
            {dashboard?.keywords?.length > 0 ? (
              <div className="max-h-[420px] overflow-y-auto">
                <div className="space-y-3">
                  {dashboard.keywords.map((item, index) => (
                    <div key={index} className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-medium text-slate-900">{item.keyword}</p>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${item.hasAIOverview ? "bg-blue-100 text-blue-700" : "bg-slate-200 text-slate-700"}`}>
                          {item.hasAIOverview ? "AIO" : "No AIO"}
                        </span>
                      </div>
                      {item.aiOverviewText && (
                        <p className="text-sm text-slate-600 line-clamp-2">{item.aiOverviewText}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-slate-500">No AIO data yet. Click refresh to track.</p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Citation Share of Voice</h2>
            {citations.length > 0 ? (
              <div className="max-h-[420px] overflow-y-auto">
                <div className="space-y-3">
                  {citations.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div>
                        <p className="font-medium text-slate-900">{item.domain}</p>
                        <p className="text-xs text-slate-500">{item.count} citations</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-slate-900">{item.percentage}%</p>
                        <div className="w-24 h-2 bg-slate-200 rounded-full mt-1">
                          <div className="h-2 bg-blue-600 rounded-full" style={{ width: `${item.percentage}%` }} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-slate-500">No citation data yet. Click refresh to track.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
