import React, { Component, ComponentType } from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  resetOnNavigate?: boolean;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private previousPathname: string = '';

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error info:', errorInfo);
    console.error('Component stack:', errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  componentDidMount(): void {
    if (this.props.resetOnNavigate) {
      this.previousPathname = window.location.pathname;
      window.addEventListener('popstate', this.handleNavigationChange);
    }
  }

  componentDidUpdate(): void {
    if (this.props.resetOnNavigate && this.state.hasError) {
      const currentPathname = window.location.pathname;
      if (this.previousPathname !== currentPathname) {
        this.previousPathname = currentPathname;
        this.resetError();
      }
    }
  }

  componentWillUnmount(): void {
    if (this.props.resetOnNavigate) {
      window.removeEventListener('popstate', this.handleNavigationChange);
    }
  }

  handleNavigationChange = (): void => {
    if (this.state.hasError) {
      this.resetError();
    }
  };

  resetError = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    this.props.onReset?.();
  };

  handleTryAgain = (): void => {
    window.location.reload();
  };

  handleGoBack = (): void => {
    window.location.href = '/';
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-surface-muted text-text-primary px-4 py-6">
          <div className="w-full max-w-xl mx-auto">
            <div className="relative bg-surface rounded-[2rem] shadow-card border border-slate-100/70">
              <div className="px-6 pt-10 pb-8 sm:px-12 sm:pt-12 text-center">
                <div className="mb-6">
                  <svg
                    className="w-16 h-16 mx-auto text-danger"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                    />
                  </svg>
                </div>
                <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mb-4">
                  Something went wrong
                </h1>
                <p className="mx-auto max-w-2xl text-base sm:text-lg leading-relaxed text-text-secondary">
                  We encountered an unexpected error. Don't worry, your data is safe. You can try again or go back to the home page.
                </p>
              </div>

              <div className="h-px bg-slate-200/70 mx-6 sm:mx-12" />

              <div className="px-6 py-8 sm:px-12 sm:py-12">
                <div className="space-y-4">
                  <button
                    type="button"
                    onClick={this.handleTryAgain}
                    className={
                      'inline-flex w-full items-center justify-center rounded-xl bg-brand-600 text-white text-sm font-semibold py-3.5 px-4 shadow-md transition-all duration-200 ease-out ' +
                      'hover:bg-brand-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0'
                    }
                  >
                    Try Again
                  </button>
                  <button
                    type="button"
                    onClick={this.handleGoBack}
                    className={
                      'inline-flex w-full items-center justify-center rounded-xl bg-surface text-text-primary text-sm font-semibold py-3.5 px-4 border border-slate-200 shadow-sm transition-all duration-200 ease-out ' +
                      'hover:bg-slate-50 hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0'
                    }
                  >
                    Go Back
                  </button>
                </div>
              </div>

              {process.env.NODE_ENV === 'development' && this.state.error && (
                <>
                  <div className="h-px bg-slate-200/70 mx-6 sm:mx-12" />
                  <div className="px-6 py-6 sm:px-12 sm:py-8">
                    <details className="text-left">
                      <summary className="text-sm font-medium text-text-secondary cursor-pointer hover:text-text-primary transition-colors">
                        Technical Details (Development Only)
                      </summary>
                      <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200 overflow-auto max-h-48">
                        <p className="text-sm font-mono text-danger break-all">
                          {this.state.error.toString()}
                        </p>
                        {this.state.errorInfo?.componentStack && (
                          <pre className="mt-3 text-xs font-mono text-text-secondary whitespace-pre-wrap break-all">
                            {this.state.errorInfo.componentStack}
                          </pre>
                        )}
                      </div>
                    </details>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function withErrorBoundary<P extends object>(
  WrappedComponent: ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component';

  const WithErrorBoundary = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundary.displayName = `WithErrorBoundary(${displayName})`;

  return WithErrorBoundary;
}

export { ErrorBoundary, withErrorBoundary };
export default ErrorBoundary;
