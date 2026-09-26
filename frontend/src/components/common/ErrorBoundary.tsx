import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[HealthSetu ErrorBoundary caught error]:', error, errorInfo);
    this.setState({ error, errorInfo });
    (window as any).__healthsetu_last_error = {
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
    };
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.hash = '';
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6 bg-[#FAF8F3]">
          <div className="max-w-lg w-full bg-white border border-[#DDD9D1] rounded-sm p-8 shadow-sm space-y-4">
            <div className="flex items-center gap-3 text-[#D94F7A]">
              <div className="w-10 h-10 rounded-sm bg-[#FDEEF4] border border-[#F8D2DF] flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-[#D94F7A]" />
              </div>
              <div>
                <h3 className="font-serif text-lg text-[#1C2B3A]">
                  {this.props.fallbackTitle || 'Component Recovered Gracefully'}
                </h3>
                <p className="text-xs text-[#6B7A8D]">HealthSetu resilience layer prevented screen blackout</p>
              </div>
            </div>

            <div className="p-3 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm text-xs font-mono text-[#D94F7A] overflow-x-auto max-h-36">
              {this.state.error?.message || 'An unexpected render error occurred'}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-[#DDD9D1]">
              <button
                onClick={() => {
                  window.location.reload();
                }}
                className="inline-flex items-center gap-1.5 text-xs text-[#6B7A8D] hover:text-[#1C2B3A] font-semibold"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Reload Page</span>
              </button>

              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-1.5 text-xs font-semibold bg-[#4A90C4] text-white px-4 py-2 rounded-sm hover:bg-[#3A7DB0] transition-colors"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Return to Overview</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
