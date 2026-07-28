import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import {
  getSerpFeaturesSummaryApi,
  getKeywordsWithSerpFeaturesApi,
  syncSerpFeaturesApi,
} from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";

export default function SerpFeatures() {
  const selectedProject = useSelector(selectSelectedProject);
  
  const [summary, setSummary] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
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
      const [summaryResult, keywordsResult] = await Promise.all([
        getSerpFeaturesSummaryApi(selectedProject.id),
        getKeywordsWithSerpFeaturesApi(selectedProject.id, 50)
      ]);
      
      setSummary(summaryResult.data);
      setKeywords(keywordsResult.data.keywords || []);
    } catch (err) {
      setError(err?.message || "Failed to load SERP features");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!selectedProject?.id) return;

    setSyncing(true);
    setError("");

    try {
      await syncSerpFeaturesApi(selectedProject.id);
      await loadData();
    } catch (err) {
      setError(err?.message || "Failed to sync SERP features");
    } finally {
      setSyncing(false);
    }
  };

  const getFeatureIcon = (featureType) => {
    const icons = {
      featured_snippet: "⭐",
      local_pack: "📍",
      sitelinks: "🔗",
      knowledge_panel: "📊",
      image_pack: "🖼️",
      video_pack: "🎥",
      people_also_ask: "❓",
      related_searches: "🔍",
      top_stories: "📰",
    };
    return icons[featureType] || "📋";
  };

  const getFeatureLabel = (featureType) => {
    return featureType.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (!selectedProject?.id) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <p className="text-slate-600">Please select a project to view SERP features</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 mb-1">SERP Features</h2>
          <p className="text-sm text-slate-600">Track featured snippets, local packs, and more</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "Syncing..." : "Sync Features"}
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="bg-slate-100 text-slate-700 py-2 px-4 rounded-lg font-medium hover:bg-slate-200 disabled:opacity-50"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Total Features</p>
            <p className="text-2xl font-bold text-slate-900">{summary.totalFeatures}</p>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Keywords with Features</p>
            <p className="text-2xl font-bold text-blue-600">{summary.keywordsWithFeatures}</p>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Feature Types</p>
            <p className="text-2xl font-bold text-purple-600">{Object.keys(summary.byType || {}).length}</p>
          </div>
        </div>
      )}

      {summary && summary.byType && Object.keys(summary.byType).length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-3">Features by Type</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(summary.byType).map(([type, count]) => (
              <div key={type} className="p-3 bg-slate-50 rounded-lg flex items-center gap-3">
                <span className="text-2xl">{getFeatureIcon(type)}</span>
                <div>
                  <p className="text-sm font-medium text-slate-900">{getFeatureLabel(type)}</p>
                  <p className="text-xs text-slate-600">{count} occurrences</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {keywords.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-3">Keywords with SERP Features</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Keyword</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-700">Feature Count</th>
                </tr>
              </thead>
              <tbody>
                {keywords.map((item, index) => (
                  <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 text-sm text-slate-900 font-medium">{item.keyword}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                        {item.featureCount}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {keywords.length === 0 && !loading && (
        <div className="text-center py-8">
          <p className="text-slate-600">No SERP features found.</p>
          <p className="text-sm text-slate-500 mt-1">Click "Sync Features" to analyze your rankings for SERP features.</p>
        </div>
      )}
    </div>
  );
}
