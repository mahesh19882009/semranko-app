'use client'
import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import {
  researchKeywordApi,
  competitorSpyApi,
  onboardProjectApi,
} from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";
import Input from "../components/ui/Input";

export default function KeywordResearchPage() {
  const selectedProject = useSelector(selectSelectedProject);

  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("India");
  const [loading, setLoading] = useState(false);
  const [researchData, setResearchData] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("research");

  const [spyDomain, setSpyDomain] = useState("");
  const [spyResults, setSpyResults] = useState([]);
  const [spyLoading, setSpyLoading] = useState(false);
  const [spyError, setSpyError] = useState("");

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!keyword.trim()) return;

    setLoading(true);
    setError("");
    setResearchData(null);

    try {
      const result = await researchKeywordApi(keyword, location);
      setResearchData(result.data);
    } catch (err) {
      setError(err?.message || "Failed to research keyword");
    } finally {
      setLoading(false);
    }
  };

  const handleSpy = async (e) => {
    e.preventDefault();
    if (!spyDomain.trim()) return;

    setSpyLoading(true);
    setSpyError("");
    setSpyResults([]);

    try {
      const result = await competitorSpyApi(spyDomain, location);
      setSpyResults(result.data?.keywords || []);
    } catch (err) {
       setSpyError(err?.message || "Failed to spy competitor");
    } finally {
      setSpyLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Keyword Research</h1>
          <p className="text-slate-600">Discover keywords and spy competitors</p>
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
            Research
          </button>
          <button
            onClick={() => setActiveTab("spy")}
            className={`px-4 py-2 font-medium ${
              activeTab === "spy"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Competitor Spy
          </button>
        </div>

        {error && <Alert variant="error" message={error} />}

        {activeTab === "research" && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Research a Keyword</h2>

            <form onSubmit={handleResearch} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Input
                  label="Keyword"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Enter seed keyword"
                />
                <Input
                  label="Location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="India"
                />
                <div className="flex items-end">
                  <Button type="submit" disabled={loading || !keyword.trim()} loading={loading} fullWidth>
                    Research
                  </Button>
                </div>
              </div>
            </form>

            {researchData && (
              <div className="mt-6 space-y-4">
                <h3 className="text-lg font-semibold text-slate-900">Results</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-600 mb-1">Volume</p>
                    <p className="text-2xl font-bold text-slate-900">{researchData.volume ?? "—"}</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-600 mb-1">Difficulty</p>
                    <p className="text-2xl font-bold text-slate-900">{researchData.difficulty ?? "—"}</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-600 mb-1">CPC</p>
                    <p className="text-2xl font-bold text-slate-900">{researchData.cpc ?? "—"}</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-600 mb-1">Intent</p>
                    <p className="text-2xl font-bold text-slate-900">{researchData.intent || "—"}</p>
                  </div>
                </div>

                {researchData.suggestions?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-700 mb-2">Suggestions</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {researchData.suggestions.slice(0, 20).map((item, index) => (
                        <div key={index} className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700">
                          <p className="font-medium text-slate-900">{item.keyword}</p>
                          <p className="text-xs text-slate-500">Vol: {item.volume ?? "—"} · KD: {item.difficulty ?? "—"} · CPC: {item.cpc ?? "—"}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "spy" && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Competitor Keyword Spy</h2>

            <form onSubmit={handleSpy} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Input
                  label="Competitor domain"
                  value={spyDomain}
                  onChange={(e) => setSpyDomain(e.target.value)}
                  placeholder="competitor.com"
                />
                <Input
                  label="Location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="India"
                />
                <div className="flex items-end">
                  <Button type="submit" disabled={spyLoading || !spyDomain.trim()} loading={spyLoading} fullWidth>
                    Spy
                  </Button>
                </div>
              </div>
            </form>

            {spyError && <Alert variant="error" message={spyError} />}

            {spyResults.length > 0 && (
              <div className="mt-6 overflow-x-auto">
                <div className="max-h-[420px] overflow-y-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                        <th className="text-left py-3 px-4 font-medium">Keyword</th>
                        <th className="text-left py-3 px-4 font-medium">Position</th>
                        <th className="text-left py-3 px-4 font-medium">URL</th>
                        <th className="text-left py-3 px-4 font-medium">Volume</th>
                        <th className="text-left py-3 px-4 font-medium">Difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {spyResults.map((item, index) => (
                        <tr key={index} className="border-b border-slate-100">
                          <td className="py-3 px-4 text-sm text-slate-900 font-medium">{item.keyword}</td>
                          <td className="py-3 px-4 text-sm text-slate-600">#{item.position ?? "—"}</td>
                          <td className="py-3 px-4 text-sm text-slate-600 truncate max-w-xs">{item.url || "—"}</td>
                          <td className="py-3 px-4 text-sm text-slate-600">{item.volume ?? "—"}</td>
                          <td className="py-3 px-4 text-sm text-slate-600">{item.difficulty ?? "—"}</td>
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
