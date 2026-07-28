import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { getLHFOpportunitiesApi, getLHFSummaryApi } from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "./ui/Button";

export default function LowHangingFruits() {
  const selectedProject = useSelector(selectSelectedProject);
  
  const [opportunities, setOpportunities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedProject?.id) {
      loadData();
    }
  }, [selectedProject?.id]);

  const loadData = async () => {
    if (!selectedProject?.id) return;

    setLoading(true);
    setError("");

    try {
      const [oppResult, summaryResult] = await Promise.all([
        getLHFOpportunitiesApi(selectedProject.id),
        getLHFSummaryApi(selectedProject.id)
      ]);
      
      setOpportunities(oppResult.data.opportunities || []);
      setSummary(summaryResult.data);
    } catch (err) {
      setError(err?.message || "Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case "Quick Win": return "bg-green-100 text-green-800";
      case "High Potential": return "bg-blue-100 text-blue-800";
      case "Near Top 10": return "bg-purple-100 text-purple-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getLHFColor = (score) => {
    if (score >= 70) return "text-green-600";
    if (score >= 50) return "text-blue-600";
    if (score >= 30) return "text-yellow-600";
    return "text-gray-600";
  };

  if (!selectedProject?.id) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <p className="text-slate-600">Please select a project to view low hanging fruits</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 mb-1">Low Hanging Fruits</h2>
          <p className="text-sm text-slate-600">Quick-win opportunities to improve rankings</p>
        </div>
        <Button
          onClick={loadData}
          disabled={loading}
          variant="primary"
        >
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Total Opportunities</p>
            <p className="text-2xl font-bold text-slate-900">{summary.totalOpportunities}</p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Quick Wins</p>
            <p className="text-2xl font-bold text-green-600">{summary.quickWins}</p>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">High Potential</p>
            <p className="text-2xl font-bold text-blue-600">{summary.highPotential}</p>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Avg LHF Score</p>
            <p className="text-2xl font-bold text-purple-600">{summary.averageLHFScore}</p>
          </div>
        </div>
      )}

      {opportunities.length === 0 && !loading && (
        <div className="text-center py-8">
          <p className="text-slate-600">No low hanging fruit opportunities found.</p>
          <p className="text-sm text-slate-500 mt-1">Add keywords and run rank checks to identify opportunities.</p>
        </div>
      )}

      {opportunities.length > 0 && (
        <div className="overflow-x-auto">
          <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <th className="text-left py-3 px-4 font-medium">Keyword</th>
                  <th className="text-left py-3 px-4 font-medium">Position</th>
                  <th className="text-left py-3 px-4 font-medium">Change</th>
                  <th className="text-left py-3 px-4 font-medium">Difficulty</th>
                  <th className="text-left py-3 px-4 font-medium">LHF Score</th>
                  <th className="text-left py-3 px-4 font-medium">Category</th>
                </tr>
              </thead>
              <tbody>
                {opportunities.map((opp, index) => (
                  <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 text-sm text-slate-900 font-medium">{opp.keyword}</td>
                    <td className="py-3 px-4 text-sm text-slate-600">#{opp.currentPosition}</td>
                    <td className="py-3 px-4">
                      {opp.positionChange !== 0 ? (
                        <span className={`text-sm font-medium ${opp.positionChange > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {opp.positionChange > 0 ? '+' : ''}{opp.positionChange}
                        </span>
                      ) : (
                        <span className="text-sm text-slate-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-sm font-medium ${opp.difficulty <= 40 ? 'text-green-600' : opp.difficulty <= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {opp.difficulty}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-sm font-bold ${getLHFColor(opp.lhfScore)}`}>
                        {opp.lhfScore}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(opp.category)}`}>
                        {opp.category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
