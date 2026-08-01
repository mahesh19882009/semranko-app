'use client'
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faArrowDown, faMinus, faChartLine } from '@fortawesome/free-solid-svg-icons';
import RankHistoryChart from './RankHistoryChart';
import { apiRequest, getCompetitorComparisonApi } from '../lib/api';
import Button from './ui/Button';

function CompetitorComparison({ projectId }) {
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(false);

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const loadComparisonData = async () => {
    if (!selectedProjectId) return;

    setLoading(true);
    try {
      const data = await getCompetitorComparisonApi(selectedProjectId);

      if (data.success) {
        setComparisonData(data.data.comparison || []);
      }
    } catch (error) {
      console.error('Failed to load competitor comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  const getGapIndicator = (gap) => {
    if (gap > 0) {
      return (
        <span className="text-emerald-600">
          <FontAwesomeIcon icon={faArrowUp} className="mr-1" />
          +{gap}
        </span>
      );
    } else if (gap < 0) {
      return (
        <span className="text-rose-600">
          <FontAwesomeIcon icon={faArrowDown} className="mr-1" />
          {gap}
        </span>
      );
    }
    return <span className="text-slate-500"><FontAwesomeIcon icon={faMinus} /></span>;
  };

  if (!selectedProjectId) {
    return (
      <div className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-center text-slate-500">Select a project to view competitor comparison</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Load Data Button */}
      {!comparisonData && (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft text-center">
          <Button
            onClick={loadComparisonData}
            disabled={loading}
            variant="primary"
          >
            <FontAwesomeIcon icon={faChartLine} />
            {loading ? 'Loading...' : 'Load Competitor Comparison'}
          </Button>
        </div>
      )}

      {/* Competitor Comparison Table */}
      {comparisonData && comparisonData.length > 0 && (
        <div className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Competitor Rankings</h3>
          <div className="max-h-[320px] overflow-y-auto">
            <div className="space-y-4">
              {comparisonData.map((row, idx) => (
                <div
                  key={idx}
                  className="rounded-2xl border border-slate-100 p-4 hover:border-slate-300 transition"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="font-semibold text-slate-900">{row.keyword}</p>
                      <p className="text-sm text-slate-500">
                        You: #{row.user_position || '—'}
                      </p>
                    </div>
                    <div className="text-right text-sm text-slate-600">
                      {[1, 2, 3].map((i) => (
                        <div key={i}>
                          Comp {i}: #{row[`competitor_${i}_position`] || '—'}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {comparisonData && comparisonData.length === 0 && (
        <div className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft text-center">
          <p className="text-slate-500">No competitors tracked for this project</p>
        </div>
      )}
    </div>
  );
}

export default CompetitorComparison;
