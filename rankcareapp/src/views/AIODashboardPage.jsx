'use client'
import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { getAioDashboardApi, getAioCitationsApi } from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Alert from "../components/ui/Alert";

export default function AIODashboardPage() {
  const selectedProject = useSelector(selectSelectedProject);
  const pricing = useSelector((state) => state.pricing);
  const currentPlanKey = (pricing.current?.plan || "").toLowerCase();
  const isFreeTrial = currentPlanKey === "free_trial" || !pricing.current;

  const [dashboard, setDashboard] = useState(null);
  const [citations, setCitations] = useState([]);
  const [loading, setLoading] = useState(false);
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
        <div className="mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">AIO Dashboard</h1>
            <p className="text-slate-600">Track AI Overview presence and citation share of voice</p>
          </div>
        </div>

        {isFreeTrial && (
          <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="text-3xl">🔒</div>
              <div>
                <h3 className="text-lg font-semibold text-amber-900">AI Overview tracking is a premium asset</h3>
                <p className="mt-1 text-sm text-amber-700">
                  Enable AI tracking for individual keywords in the Keywords page to see AI Overview data.
                </p>
                <button
                  onClick={() => {
                    window.location.href = "/keywords";
                  }}
                  className="mt-3 rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
                >
                  Go to Keywords
                </button>
              </div>
            </div>
          </div>
        )}

        {error && <Alert variant="error" className="mb-5" message={error} />}

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
              <p className="text-slate-500">No AIO data yet. Enable AI tracking for individual keywords in the Keywords page.</p>
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
              <p className="text-slate-500">No citation data yet. Enable AI tracking for individual keywords to see citation data.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
