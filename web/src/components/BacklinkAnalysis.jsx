import { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLink, faChartBar, faExternalLinkAlt, faSync } from '@fortawesome/free-solid-svg-icons';

function BacklinkAnalysis({ projectId }) {
  const [backlinks, setBacklinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(0);

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const loadBacklinks = async (pageNum = 1) => {
    if (!selectedProjectId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/backlinks/project/${selectedProjectId}?page=${pageNum}&page_size=${pageSize}`);
      const data = await response.json();
      
      if (data.success) {
        setBacklinks(data.data.backlinks || []);
        setTotalPages(data.data.pagination?.total_pages || 0);
        setPage(pageNum);
        
        const bls = data.data.backlinks || [];
        setStats({
          total: data.data.pagination?.total || bls.length,
          avgDomainRank: bls.length > 0 
            ? Math.round(bls.reduce((sum, bl) => sum + (bl.domainRank || 0), 0) / bls.length)
            : 0,
          uniqueDomains: [...new Set(bls.map(bl => bl.sourceDomain))].length
        });
      }
    } catch (error) {
      console.error('Failed to load backlinks:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockBacklinks = async () => {
    if (!selectedProjectId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/mock-data/backlinks/${selectedProjectId}?count=50`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        // Reload backlinks after generation
        loadBacklinks();
      }
    } catch (error) {
      console.error('Failed to generate mock backlinks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProjectId) {
      loadBacklinks();
    }
  }, [selectedProjectId]);

  if (!selectedProjectId) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-center text-slate-500">Select a project to view backlink analysis</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
                <FontAwesomeIcon icon={faLink} />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Total Backlinks
                </p>
                <p className="text-2xl font-bold text-slate-900">{stats.total}</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
                <FontAwesomeIcon icon={faChartBar} />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Avg Domain Rank
                </p>
                <p className="text-2xl font-bold text-slate-900">{stats.avgDomainRank}</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
                <FontAwesomeIcon icon={faLink} />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Unique Domains
                </p>
                <p className="text-2xl font-bold text-slate-900">{stats.uniqueDomains}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Backlink List */}
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Backlink Profile</h3>
            <p className="mt-1 text-sm text-slate-500">
              External links pointing to your domain
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadBacklinks}
              disabled={loading}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <FontAwesomeIcon icon={faSync} className="mr-2" />
              Refresh
            </button>
            <button
              onClick={generateMockBacklinks}
              disabled={loading}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Generate Mock Data
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-10 text-slate-500">Loading...</div>
        ) : backlinks.length === 0 ? (
          <div className="text-center py-10 text-slate-500">
            <p className="font-medium text-slate-700">No backlinks found</p>
            <p className="mt-2 text-sm">Generate mock data to see backlink analysis</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-slate-200 text-left text-sm text-slate-500">
                  <th className="py-3 pr-4 font-medium">Source Domain</th>
                  <th className="py-3 pr-4 font-medium">Anchor Text</th>
                  <th className="py-3 pr-4 font-medium">Domain Rank</th>
                  <th className="py-3 pr-4 font-medium">First Seen</th>
                  <th className="py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {backlinks.map((bl, idx) => (
                  <tr key={idx} className="border-b border-slate-100 text-sm">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <FontAwesomeIcon icon={faLink} className="text-slate-400" />
                        <span className="font-medium text-slate-900">{bl.sourceDomain}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-slate-600">{bl.anchor || '—'}</td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold ${
                        bl.domainRank >= 50 ? 'bg-emerald-100 text-emerald-700' :
                        bl.domainRank >= 30 ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {bl.domainRank || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-500">
                      {bl.firstSeen ? new Date(bl.firstSeen).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-3">
                      <a
                        href={bl.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800"
                      >
                        <FontAwesomeIcon icon={faExternalLinkAlt} />
                        View
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => loadBacklinks(page - 1)}
              disabled={loading || page <= 1}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
            <button
              onClick={() => loadBacklinks(page + 1)}
              disabled={loading || page >= totalPages}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default BacklinkAnalysis;
