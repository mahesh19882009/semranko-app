'use client'
import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faFolderPlus,
  faMagnifyingGlassChart,
  faPlay,
  faCheckCircle,
  faChevronRight,
} from '@fortawesome/free-solid-svg-icons';
import { useNavigate } from '../lib/navigation';
import { createProject } from '../features/projects/projectsSlice';
import { addKeywordToProject } from '../features/keywords/keywordsSlice';
import Button from './ui/Button';

const STORAGE_KEY = 'semranko_onboarding_completed';

function getInitialOnboardingState() {
  try {
    const completed = localStorage.getItem(STORAGE_KEY);
    return completed === 'true';
  } catch {
    return false;
  }
}

function OnboardingWizard({ onComplete }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const projects = useSelector((state) => state.projects.list);
  const creating = useSelector((state) => state.projects.creating);
  const adding = useSelector((state) => state.keywords.adding);

  const [step, setStep] = useState(0);
  const [projectName, setProjectName] = useState('');
  const [domain, setDomain] = useState('');
  const [keywords, setKeywords] = useState('');
  const [showOnboarding, setShowOnboarding] = useState(() => !getInitialOnboardingState());

  const isCompleted = projects.length > 0;

  useEffect(() => {
    if (isCompleted) {
      try {
        localStorage.setItem(STORAGE_KEY, 'true');
      } catch {
        // ignore
      }
      setShowOnboarding(false);
      onComplete?.();
    }
  }, [isCompleted, onComplete]);

  const handleCreateProject = async (e) => {
    e.preventDefault();
    const result = await dispatch(
      createProject({
        name: projectName || 'My First Project',
        domain: domain || 'example.com',
      })
    );

    if (createProject.fulfilled.match(result)) {
      setStep(1);
    }
  };

  const handleAddKeywords = async (e) => {
    e.preventDefault();
    const keywordList = keywords
      .split(/[\n,]+/)
      .map((k) => k.trim())
      .filter(Boolean);

    if (keywordList.length === 0) return;

    const selectedProjectId = projects[0]?.id;
    if (!selectedProjectId) return;

    for (const keyword of keywordList) {
      await dispatch(
        addKeywordToProject({
          projectId: selectedProjectId,
          payload: { keyword, location: 'India', device: 'desktop' },
        })
      );
    }

    setStep(2);
  };

  const handleFinish = () => {
    try {
      localStorage.setItem(STORAGE_KEY, 'true');
    } catch {
      // ignore
    }
    setShowOnboarding(false);
    onComplete?.();
    navigate('/keywords');
  };

  const steps = [
    {
      title: 'Create your first project',
      description: 'Set up a project to start tracking your SEO rankings.',
      icon: faFolderPlus,
      color: 'bg-brand-600',
    },
    {
      title: 'Add keywords to track',
      description: 'Enter the keywords you want to monitor for your project.',
      icon: faMagnifyingGlassChart,
      color: 'bg-emerald-600',
    },
    {
      title: 'Run your first rank check',
      description: 'Check where your keywords rank in search results.',
      icon: faPlay,
      color: 'bg-amber-600',
    },
  ];

  if (!showOnboarding) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-lg rounded-xs bg-white shadow-soft">
        <div className="p-6">
          {/* Progress */}
          <div className="mb-6 flex items-center justify-between">
            {steps.map((s, index) => (
              <div key={index} className="flex items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white ${
                    index <= step ? s.color : 'bg-slate-200 text-slate-400'
                  }`}
                >
                  {index < step ? <FontAwesomeIcon icon={faCheckCircle} /> : index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div className={`h-0.5 w-8 ${index < step ? 'bg-brand-600' : 'bg-slate-200'}`} />
                )}
              </div>
            ))}
          </div>

          <div className="mb-6">
            <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl ${steps[step].color} text-white`}>
              <FontAwesomeIcon icon={steps[step].icon} className="text-lg" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">{steps[step].title}</h2>
            <p className="mt-1 text-sm text-slate-500">{steps[step].description}</p>
          </div>

          {step === 0 && (
            <form onSubmit={handleCreateProject} className="space-y-4">
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Project name"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
                required
              />
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="Domain (example.com)"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
                required
              />
              <Button
                type="submit"
                disabled={creating}
                variant="primary"
              >
                {creating ? 'Creating...' : 'Create project'}
                <FontAwesomeIcon icon={faChevronRight} />
              </Button>
            </form>
          )}

          {step === 1 && (
            <form onSubmit={handleAddKeywords} className="space-y-4">
              <textarea
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="Enter keywords (comma or newline separated)"
                rows={4}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none resize-none"
                required
              />
              <Button
                type="submit"
                disabled={adding}
                variant="primary"
              >
                {adding ? 'Adding...' : 'Add keywords'}
                <FontAwesomeIcon icon={faChevronRight} />
              </Button>
            </form>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                Great! Your project and keywords are set up. You can now run rank checks from the Keywords page.
              </p>
              <Button
                type="button"
                onClick={handleFinish}
                variant="primary"
              >
                Go to Keywords
                <FontAwesomeIcon icon={faChevronRight} />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function useOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(() => !getInitialOnboardingState());

  useEffect(() => {
    try {
      const completed = localStorage.getItem(STORAGE_KEY);
      if (completed === 'true') {
        setShowOnboarding(false);
      }
    } catch {
      // ignore
    }
  }, []);

  const completeOnboarding = () => {
    setShowOnboarding(false);
  };

  return { showOnboarding, completeOnboarding };
}

export default OnboardingWizard;
