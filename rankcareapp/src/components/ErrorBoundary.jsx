'use client'
import { Component } from 'react';
import Button from './ui/Button';

function ErrorBoundary({ children, fallback }) {
  class Boundary extends Component {
    state = { hasError: false, error: null };

    static getDerivedStateFromError(error) {
      return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
      if (process.env.NODE_ENV !== 'production') {
        console.error('UI error caught by boundary:', error, errorInfo);
      }
    }

    render() {
      if (this.state.hasError) {
        if (fallback) {
          return fallback(this.state.error);
        }

        return (
          <div className="flex min-h-[400px] items-center justify-center p-6">
            <div className="max-w-md rounded-xs border border-rose-200 bg-white p-8 text-center shadow-soft">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-2xl">
                ⚠️
              </div>
              <h2 className="text-lg font-semibold text-slate-900">Something went wrong</h2>
              <p className="mt-2 text-sm text-slate-600">
                An unexpected error occurred. Your data is safe; please try again.
              </p>
              <div className="mt-5 flex justify-center gap-3">
                <Button type="button" onClick={() => this.setState({ hasError: false, error: null })} variant="primary">
                  Try again
                </Button>
                <Button type="button" onClick={() => { window.location.href = '/dashboard'; }} variant="secondary">
                  Return to Dashboard
                </Button>
              </div>
            </div>
          </div>
        );
      }

      return children;
    }
  }

  return <Boundary />;
}

export default ErrorBoundary;
