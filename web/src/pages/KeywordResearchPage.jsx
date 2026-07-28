import { useState } from "react";
import { useSelector } from "react-redux";
import { researchKeywordApi, getKeywordOpportunitiesApi } from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

export default function KeywordResearchPage() {
  const selectedProject = useSelector(selectSelectedProject);
  
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [researchData, setResearchData] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [loadingOpportunities, setLoadingOpportunities] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("research");

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!keyword.trim() || !selectedProject?.id) return;

    setLoading(true);
    setError("");
    setResearchData(null);

    try {
      const result = await researchKeywordApi(keyword, selectedProject.id);
      setResearchData(result.data);
    } catch (err) {
      setError(err?.message || "Failed to research keyword");
    } finally {
      setLoading(false);
    }
  };

  const loadOpportunities = async () => {
    if (!selectedProject?.id) return;

    setLoadingOpportunities(true);
    setError("");

    try {
      const result = await getKeywordOpportunitiesApi(selectedProject.id);
      setOpportunities(result.data.opportunities || []);
    } catch (err) {
      setError(err?.message || "Failed to load opportunities");
    } finally {
      setLoadingOpportunities(false);
    }
  };

  const getDifficultyColor = (difficulty) => {
    if (difficulty <= 30) return "text-green-600 bg-green-50";
    if (difficulty <= 60) return "text-yellow-600 bg-yellow-50";
    return "text-red-600 bg-red-50";
  };

  const getDifficultyLabel = (difficulty) => {
    if (difficulty <= 30) return "Easy";
    if (difficulty <= 60) return "Medium";
    return "Hard";
  };

  const getOpportunityColor = (score) => {
    if (score >= 70) return "text-green-600 bg-green-50";
    if (score >= 40) return "text-yellow-600 bg-yellow-50";
    return "text-gray-600 bg-gray-50";
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Keyword Research</h1>
          <p className="text-slate-600">Discover keyword opportunities and analyze difficulty</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-slate-200">
          <button
            onClick={() => setActiveTab("research")}
            className={`px-4 py-2 font-medium ${
              activeTab === "research"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Research Keyword
          </button>
          <button
            onClick={() => {
              setActiveTab("opportunities");
              loadOpportunities();
            }}
            className={`px-4 py-2 font-medium ${
              activeTab === "opportunities"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Opportunities
          </button>
        </div>

        {error && (
          <Alert variant="error" message={error} />
        )}

        {activeTab === "research" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Research Form */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Research a Keyword</h2>
              
              <form onSubmit={handleResearch}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Keyword
                  </label>
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="Enter a keyword to research"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={!selectedProject?.id}
                  />
                  {!selectedProject?.id && (
                    <p className="mt-1 text-sm text-red-600">Please select a project first</p>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={loading || !keyword.trim() || !selectedProject?.id}
                  loading={loading}
                  fullWidth
                >
                  Research Keyword
                </Button>
              </form>

              {researchData && (
                <div className="mt-6 space-y-4">
                  <h3 className="text-lg font-semibold text-slate-900">Results</h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <p className="text-sm text-slate-600 mb-1">Difficulty</p>
                      <p className={`text-2xl font-bold ${getDifficultyColor(researchData.difficulty).split(' ')[0]}`}>
                        {researchData.difficulty}
                      </p>
                      <p className={`text-xs font-medium ${getDifficultyColor(researchData.difficulty)}`}>
                        {getDifficultyLabel(researchData.difficulty)}
                      </p>
                    </div>
                    
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <p className="text-sm text-slate-600 mb-1">Search Volume</p>
                      <p className="text-2xl font-bold text-slate-900">
                        {researchData.searchVolume.toLocaleString()}
                      </p>
                      <p className="text-xs text-slate-600">Monthly searches</p>
                    </div>
                    
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <p className="text-sm text-slate-600 mb-1">Opportunity Score</p>
                      <p className={`text-2xl font-bold ${getOpportunityColor(researchData.opportunityScore).split(' ')[0]}`}>
                        {researchData.opportunityScore}
                      </p>
                      <p className="text-xs text-slate-600">Out of 100</p>
                    </div>
                  </div>

                  {researchData.suggestions && researchData.suggestions.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-slate-700 mb-2">Suggestions</h4>
                      <div className="space-y-2">
                        {researchData.suggestions.map((suggestion, index) => (
                          <div
                            key={index}
                            className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700"
                          >
                            {suggestion.keyword}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {researchData.relatedKeywords && researchData.relatedKeywords.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-slate-700 mb-2">Related Keywords</h4>
                      <div className="space-y-2">
                        {researchData.relatedKeywords.map((related, index) => (
                          <div
                            key={index}
                            className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700"
                          >
                            {related.keyword}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Info Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">About Keyword Research</h2>
              <div className="space-y-4 text-sm text-slate-600">
                <div>
                  <h3 className="font-medium text-slate-900 mb-1">Difficulty Score</h3>
                  <p>Estimates how hard it is to rank for this keyword. Lower scores indicate easier ranking opportunities.</p>
                </div>
                <div>
                  <h3 className="font-medium text-slate-900 mb-1">Search Volume</h3>
                  <p>Estimated monthly search volume. Higher volume means more potential traffic.</p>
                </div>
                <div>
                  <h3 className="font-medium text-slate-900 mb-1">Opportunity Score</h3>
                  <p>Combines difficulty and search volume to identify the best keyword opportunities.</p>
                </div>
                <div>
                  <h3 className="font-medium text-slate-900 mb-1">Suggestions</h3>
                  <p>Related keyword suggestions from Google Autocomplete to expand your keyword list.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "opportunities" && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900">Keyword Opportunities</h2>
              <Button
                onClick={loadOpportunities}
                disabled={loadingOpportunities || !selectedProject?.id}
                loading={loadingOpportunities}
              >
                Refresh
              </Button>
            </div>

            {!selectedProject?.id && (
              <p className="text-slate-600">Please select a project to view opportunities</p>
            )}

            {opportunities.length === 0 && !loadingOpportunities && selectedProject?.id && (
              <p className="text-slate-600">No opportunities found. Add keywords and run rank checks first.</p>
            )}

            {opportunities.length > 0 && (
              <div className="overflow-x-auto">
                <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                        <th className="text-left py-3 px-4 font-medium">Keyword</th>
                        <th className="text-left py-3 px-4 font-medium">Current Position</th>
                        <th className="text-left py-3 px-4 font-medium">Difficulty</th>
                        <th className="text-left py-3 px-4 font-medium">Search Volume</th>
                        <th className="text-left py-3 px-4 font-medium">Opportunity Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opportunities.map((opp, index) => (
                        <tr key={index} className="border-b border-slate-100">
                          <td className="py-3 px-4 text-sm text-slate-900 font-medium">{opp.keyword}</td>
                          <td className="py-3 px-4 text-sm text-slate-600">#{opp.currentPosition}</td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(opp.difficulty)}`}>
                              {opp.difficulty}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600">{opp.searchVolume.toLocaleString()}</td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOpportunityColor(opp.opportunityScore)}`}>
                              {opp.opportunityScore}
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
        )}
      </div>
    </div>
  );
}
