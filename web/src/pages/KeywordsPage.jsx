import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import KeywordTable from '../components/KeywordTable';
import {
  clearKeywordsState,
  fetchKeywordsByProject,
  fetchRankingsByProject,
} from '../features/keywords/keywordsSlice';
import Alert from '../components/ui/Alert';

function KeywordsPage() {
  const dispatch = useDispatch();

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const projectsLoading = useSelector((state) => state.projects.loading);

  const pricingCurrent = useSelector((state) => state.pricing.current);

  const keywordLimitReached = (pricingCurrent?.usage?.keywords || 0) >= (pricingCurrent?.limits?.keywords || 0);


  useEffect(() => {
    if (projectsLoading) return;

    if (!selectedProjectId) {
      dispatch(clearKeywordsState());
      return;
    }

    dispatch(fetchKeywordsByProject(selectedProjectId));
    dispatch(fetchRankingsByProject(selectedProjectId));
  }, [dispatch, selectedProjectId, projectsLoading]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Keywords</h2>
        <p className="mt-1 text-sm text-slate-500">
          Manage tracked keywords and run rank checks for the selected project.
        </p>
        <p className="text-sm text-slate-500">
          Usage: {pricingCurrent?.usage?.keywords || 0} / {pricingCurrent?.limits?.keywords || 0} keywords used.
        </p>
      </div>

      { keywordLimitReached ? (
        <Alert
          variant="warning"
          message="You have reached your keyword limit for the current plan. Upgrade to track more keywords."
        />
      ) : null}

      <KeywordTable />
    </div>
  );
}

export default KeywordsPage;