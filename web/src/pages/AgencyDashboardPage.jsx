import { useState, useEffect } from "react";
import {
  getAgencyOverviewApi,
  getProjectComparisonApi,
  getRoiMetricsApi,
} from "../lib/api";
import { formatDate } from "../utils/date";

export default function AgencyDashboardPage() {
  const [overview, setOverview] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [roi, setRoi] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError("");

    try {
      const [overviewResult, comparisonResult, roiResult] = await Promise.all([
        getAgencyOverviewApi(),
        getProjectComparisonApi(),
        getRoiMetricsApi(),
      ]);

      setOverview(overviewResult.data);
      setComparison(comparisonResult.data.comparison || []);
      setRoi(roiResult.data);
    } catch (err) {
      setError(err?.message || "Failed to load agency dashboard data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-slate-600">Loading agency dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Agency Dashboard</h1>
          <p className="text-slate-600">Overview of all your projects and performance metrics</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* ROI Metrics */}
        {roi && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Total Projects</p>
              <p className="text-3xl font-bold text-slate-900">{roi.projectCount}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Total Keywords</p>
              <p className="text-3xl font-bold text-slate-900">{roi.totalKeywords}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Top 10 Rankings</p>
              <p className="text-3xl font-bold text-green-600">{roi.totalTop10}</p>
              <p className="text-sm text-slate-500">{roi.top10Percentage}% of total</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-1">Top 3 Rankings</p>
              <p className="text-3xl font-bold text-blue-600">{roi.totalTop3}</p>
              <p className="text-sm text-slate-500">{roi.top3Percentage}% of total</p>
            </div>
          </div>
        )}

        {/* Project Comparison */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Project Performance</h2>
          
          {comparison.length === 0 ? (
            <p className="text-slate-600">No projects to compare</p>
          ) : (
            <div className="overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200 sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                      <th className="text-left py-3 px-4 font-medium">Project</th>
                      <th className="text-left py-3 px-4 font-medium">Domain</th>
                      <th className="text-left py-3 px-4 font-medium">Keywords</th>
                      <th className="text-left py-3 px-4 font-medium">Top 10</th>
                      <th className="text-left py-3 px-4 font-medium">Top 10 %</th>
                      <th className="text-left py-3 px-4 font-medium">Improved (30d)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.map((project, index) => (
                      <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4 text-sm font-medium text-slate-900">{project.projectName}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">{project.domain}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">{project.keywordCount}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">{project.top10Count}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            project.top10Percentage >= 50 ? 'bg-green-100 text-green-800' :
                            project.top10Percentage >= 20 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {project.top10Percentage}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600">{project.improvedCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Top Performers */}
        {overview && overview.topPerformers && overview.topPerformers.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Top Performing Projects</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {overview.topPerformers.map((project, index) => (
                <div key={index} className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="font-medium text-slate-900">{project.projectName}</p>
                  <p className="text-sm text-slate-600 mt-1">Avg Rank: #{project.averageRank}</p>
                  <p className="text-xs text-slate-500">{project.keywordCount} keywords</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Activity */}
        {overview && overview.recentActivity && overview.recentActivity.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Recent Activity</h2>
            <div className="max-h-[320px] overflow-y-auto">
              <div className="space-y-3">
                {overview.recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{activity.keyword}</p>
                      <p className="text-xs text-slate-600">{activity.projectName}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-slate-900">#{activity.position}</p>
                      <p className="text-xs text-slate-500">
                        {formatDate(activity.checkedAt)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
