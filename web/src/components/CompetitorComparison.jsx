import { useState } from 'react';
import { useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faArrowDown, faMinus, faChartLine } from '@fortawesome/free-solid-svg-icons';
import RankHistoryChart from './RankHistoryChart';
import { apiRequest } from '../lib/api';
import Button from './ui/Button';

function CompetitorComparison({ projectId }) {
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [opportunities, setOpportunities] = useState(null);
  const [loading, setLoading] = useState(false);

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const loadComparisonData = async () => {
    if (!selectedProjectId) return;
    
    setLoading(true);
    try {
      // Fetch comparison data from API
      const data = await apiRequest(`/competitor-rankings/comparison/${selectedProjectId}`);
      
      if (data.success) {
        setComparisonData(data.data.competitors);
      }

      // Fetch opportunities
      const oppData = await apiRequest(`/competitor-rankings/opportunities/${selectedProjectId}`);
      
      if (oppData.success) {
        setOpportunities(oppData.data.opportunities);
      }
    } catch (error) {
      console.error('Failed to load competitor comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCompetitorHistory = async (competitorId) => {
    if (!selectedProjectId || !competitorId) return;
    
    try {
      const data = await apiRequest(`/competitor-rankings/history/${selectedProjectId}/${competitorId}?days=30`);
      
      if (data.success) {
        setSelectedCompetitor({
          ...selectedCompetitor,
          history: data.data.history
        });
      }
    } catch (error) {
      console.error('Failed to load competitor history:', error);
    }
  };

  const handleCompetitorClick = (competitor) => {
    setSelectedCompetitor(competitor);
    setShowHistory(true);
    loadCompetitorHistory(competitor.competitor_id);
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
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
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

      {/* Keyword Opportunities */}
      {opportunities && opportunities.length > 0 && (
        <div className="rounded-3xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-6 shadow-soft">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Keyword Opportunities</h3>
          <div className="space-y-3">
            {opportunities.slice(0, 5).map((opp, idx) => (
              <div key={idx} className="rounded-2xl border border-amber-100 bg-white p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-900">{opp.keyword}</p>
                    <p className="text-sm text-slate-500">
                      Your position: #{opp.your_position}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-rose-600 font-semibold">
                      {opp.competitors_outranking.length} competitors ahead
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitor Comparison Table */}
      {comparisonData && comparisonData.length > 0 && (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Competitor Rankings</h3>
          <div className="max-h-[320px] overflow-y-auto">
            <div className="space-y-4">
              {comparisonData.map((competitor) => (
                <div
                  key={competitor.competitor_id}
                  className="rounded-2xl border border-slate-100 p-4 hover:border-slate-300 transition cursor-pointer"
                  onClick={() => handleCompetitorClick(competitor)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="font-semibold text-slate-900">{competitor.competitor_name}</p>
                      <p className="text-sm text-slate-500">{competitor.competitor_domain}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-slate-500">Overlap</p>
                      <p className="font-semibold text-slate-900">{competitor.overlapPercentage}%</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500">Shared Keywords</p>
                      <p className="font-semibold text-slate-900">{competitor.shared_keywords}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Average Gap</p>
                      <p className="font-semibold text-slate-900">
                        {getGapIndicator(competitor.average_gap)}
                      </p>
                    </div>
                  </div>

                  {/* Top 5 keyword comparisons */}
                  <div className="mt-4 pt-4 border-t border-slate-100">
                    <p className="text-xs font-semibold text-slate-500 mb-2">Top Keywords</p>
                    <div className="space-y-2">
                      {competitor.rankings.slice(0, 5).map((ranking, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <span className="text-slate-600 truncate w-1/2">{ranking.keyword}</span>
                          <div className="flex items-center gap-4">
                            <span className="text-slate-500">You: #{ranking.your_position || '—'}</span>
                            <span className="text-slate-500">Them: #{ranking.competitor_position || '—'}</span>
                            <span>{getGapIndicator(ranking.gap)}</span>
                          </div>
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

      {/* Competitor History Modal */}
      {showHistory && selectedCompetitor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">
                {selectedCompetitor.competitor_name} - Rank History
              </h3>
              <button
                onClick={() => {
                  setShowHistory(false);
                  setSelectedCompetitor(null);
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            {selectedCompetitor.history && selectedCompetitor.history.length > 0 ? (
              <div className="space-y-6">
                {selectedCompetitor.history.slice(0, 3).map((keywordHistory, idx) => (
                  <div key={idx}>
                    <h4 className="font-semibold text-slate-900 mb-2">{keywordHistory.keyword}</h4>
                    <RankHistoryChart
                      data={keywordHistory.positions}
                      keyword={keywordHistory.keyword}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-slate-500">No history data available</p>
            )}
          </div>
        </div>
      )}

      {comparisonData && comparisonData.length === 0 && (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft text-center">
          <p className="text-slate-500">No competitors tracked for this project</p>
        </div>
      )}
    </div>
  );
}

export default CompetitorComparison;
