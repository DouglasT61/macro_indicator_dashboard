import React from 'react';

import { DashboardPage } from './pages/DashboardPage';

interface RootState {
  hasError: boolean;
  message: string;
}

class RootErrorBoundary extends React.Component<React.PropsWithChildren, RootState> {
  constructor(props: React.PropsWithChildren) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): RootState {
    return {
      hasError: true,
      message: error.message || 'Unknown render error',
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Root render failure', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-shell">
          <section className="panel-shell">
            <h1>Frontend Render Error</h1>
            <p>{this.state.message}</p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

export default function App() {
  return (
    <RootErrorBoundary>
      <DashboardPage />
    </RootErrorBoundary>
  );
}
