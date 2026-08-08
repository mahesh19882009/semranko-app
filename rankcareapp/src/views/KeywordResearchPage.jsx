'use client'
import { useState, useMemo } from "react";
import { useSelector } from "react-redux";
import { Chart } from 'primereact/chart';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import {
  researchKeywordApi,
  competitorSpyApi,
} from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";
import Input from "../components/ui/Input";
import CountrySelector from "../components/CountrySelector";
import { getCountryCode } from "../data/locations";

const STORAGE_KEY = 'rankcare_keyword_research_cache';
const SPY_STORAGE_KEY = 'rankcare_competitor_spy_cache';

function loadCachedResearch() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveCachedResearch(data) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore storage errors
  }
}

function loadCachedSpy() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(SPY_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveCachedSpy(data) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(SPY_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore storage errors
  }
}

export default function KeywordResearchPage() {
  const selectedProject = useSelector(selectSelectedProject);

  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("India");
  const [countryCode, setCountryCode] = useState(2356);
  const [loading, setLoading] = useState(false);
  const [researchData, setResearchData] = useState(() => loadCachedResearch());
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("research");

  const [spyDomain, setSpyDomain] = useState("");
  const [spyResults, setSpyResults] = useState(() => {
    const cached = loadCachedSpy();
    return cached?.keywords || [];
  });
  const [spyLoading, setSpyLoading] = useState(false);
  const [spyError, setSpyError] = useState("");

  // Prepare chart data for keyword research - top suggestions by volume
  const keywordChartData = useMemo(() => {
    if (!researchData || !researchData.suggestions?.length) return null;

    const sorted = [...researchData.suggestions]
      .filter(s => s.volume != null)
      .sort((a, b) => (b.volume || 0) - (a.volume || 0))
      .slice(0, 5);

    if (!sorted.length) return null;

    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
    return {
      labels: sorted.map(s => s.keyword),
      datasets: [{
        label: 'Search Volume',
        data: sorted.map(s => s.volume || 0),
        backgroundColor: colors.slice(0, sorted.length),
        borderWidth: 2,
        borderColor: '#ffffff',
      }],
    };
  }, [researchData]);

  const keywordChartOptions = {
    cutout: '60%',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          boxWidth: 12,
          padding: 16,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
    },
  };

  // Prepare chart data for competitor spy results
  const spyChartData = useMemo(() => {
    if (!spyResults || spyResults.length === 0) return null;

    const top5 = spyResults.slice(0, 5);
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
    return {
      labels: top5.map(k => k.domain || 'Unknown'),
      datasets: [{
        label: 'Shared Keywords',
        data: top5.map(k => k.intersections || 0),
        backgroundColor: colors.slice(0, top5.length),
        borderWidth: 2,
        borderColor: '#ffffff',
      }],
    };
  }, [spyResults]);

  const spyChartOptions = {
    cutout: '60%',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          boxWidth: 12,
          padding: 16,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
    },
  };

  const handleCountryChange = (selectedCountry) => {
    setCountry(selectedCountry);
    setCountryCode(getCountryCode(selectedCountry));
  };

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!keyword.trim()) return;

    setLoading(true);
    setError("");
    setResearchData(null);

    try {
      const result = await researchKeywordApi(keyword, countryCode, country);
      const data = result.data;
      setResearchData(data);
      saveCachedResearch(data);
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
      const result = await competitorSpyApi(spyDomain, countryCode, country);
      const keywords = result.data?.keywords || [];
      setSpyResults(keywords);
      saveCachedSpy({ keywords, domain: spyDomain });
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
            className={`px-4 py-2 font-medium ${activeTab === "research"
              ? "text-blue-600 border-b-2 border-blue-600"
              : "text-slate-600 hover:text-slate-900"
              }`}
          >
            Research
          </button>
          <button
            onClick={() => setActiveTab("spy")}
            className={`px-4 py-2 font-medium ${activeTab === "spy"
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
                <CountrySelector value={country} onChange={handleCountryChange} />
                <div className="flex items-end">
                  <Button type="submit" disabled={loading || !keyword.trim()} loading={loading} fullWidth>
                    Research
                  </Button>
                </div>
              </div>
            </form>

            {researchData && (
              <div className="mt-6 space-y-4">
                <h3 className="text-lg font-semibold text-slate-900">
                  Results for "{researchData.seed || keyword}"
                </h3>

                {/* Suggestions Chart */}
                {keywordChartData && (
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div>
                      <Chart type="doughnut" data={keywordChartData} options={keywordChartOptions} />
                    </div>
                  </div>
                )}

                {/* Suggestions Table */}
                <h2 className="text-xl font-semibold text-slate-900 mb-4">Suggestions</h2>
                {researchData.suggestions?.length > 0 && (
                  <div className="rounded-xs border border-slate-200 bg-white shadow-soft">
                     <DataTable
                      value={researchData.suggestions}
                      paginator
                      rows={10}
                      size="small"
                      rowsPerPageOptions={[10, 20, 50]}
                      sortField="volume"
                      sortOrder={-1}
                      removableSort
                      dataKey="keyword"
                      emptyMessage="No suggestions found."
                      tableStyle={{ minWidth: '50rem', width: '100%' }}
                      scrollable
                      scrollHeight="flex"
                      frozenWidth="14rem"
                    >
                      <Column field="keyword" header="Keyword" sortable frozen style={{ fontWeight: 600, minWidth: '14rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
                      <Column field="volume" header="Volume" sortable style={{ width: '8rem' }} body={(rowData) => rowData.volume ?? "—"} />
                      <Column field="difficulty" header="Difficulty" sortable style={{ width: '8rem' }} body={(rowData) => rowData.difficulty ?? "—"} />
                      <Column field="cpc" header="CPC" sortable style={{ width: '7rem' }} body={(rowData) => rowData.cpc != null ? `₹${rowData.cpc}` : '—'} />
                      <Column field="intent" header="Intent" style={{ width: '8rem' }} body={(rowData) => <span className="capitalize">{rowData.intent || '—'}</span>} />
                    </DataTable>
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
                <CountrySelector value={country} onChange={handleCountryChange} />
                <div className="flex items-end !mb-[2px]">
                  <Button className="!h-[45px]" type="submit" disabled={spyLoading || !spyDomain.trim()} loading={spyLoading} fullWidth>
                    Spy
                  </Button>
                </div>
              </div>
            </form>

            {spyError && <Alert variant="error" message={spyError} />}

            {spyResults.length > 0 && (
              <div className="mt-6 space-y-4">
                {/* Competitor Spy Chart */}
                {spyChartData && (
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div>
                      <Chart type="doughnut" data={spyChartData} options={spyChartOptions} />
                    </div>
                  </div>
                )}

                <div className="rounded-xs border border-slate-200 bg-white shadow-soft">
                   <DataTable
                    value={spyResults}
                    paginator
                    rows={10}
                    rowsPerPageOptions={[10, 20, 50]}
                    sortField="organic_keywords"
                    sortOrder={-1}
                    removableSort
                    dataKey="domain"
                    size="small"
                    emptyMessage="No competitors found."
                    tableStyle={{ minWidth: '60rem', width: '100%' }}
                    scrollable
                    scrollHeight="flex"
                    frozenWidth="14rem"
                  >
                    <Column field="domain" header="Competitor Domain" sortable frozen style={{ fontWeight: 600, minWidth: '14rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
                    <Column field="avg_position" header="Avg Position" sortable style={{ width: '10rem' }} body={(rowData) => rowData.avg_position != null ? Number(rowData.avg_position).toFixed(1) : "—"} />
                    <Column field="intersections" header="Shared Keywords" sortable style={{ width: '10rem' }} body={(rowData) => rowData.intersections != null ? Number(rowData.intersections).toLocaleString() : "—"} />
                    <Column field="organic_keywords" header="Organic Keywords" sortable style={{ width: '12rem' }} body={(rowData) => rowData.organic_keywords != null ? Number(rowData.organic_keywords).toLocaleString() : "—"} />
                    <Column field="etv" header="ETV" style={{ width: '12rem' }} body={(rowData) => rowData.etv != null ? `$${Number(rowData.etv).toLocaleString('en-US', { maximumFractionDigits: 0 })}` : "—"} />
                    <Column field="paid_traffic_cost" header="Paid Traffic Cost" sortable style={{ width: '14rem' }} body={(rowData) => rowData.paid_traffic_cost != null ? `$${Number(rowData.paid_traffic_cost).toLocaleString('en-US', { maximumFractionDigits: 0 })}` : "—"} />
                  </DataTable>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
