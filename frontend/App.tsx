
import React, { useCallback, useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './store/AuthContext';
import { DataProvider } from './store/DataContext';
import Layout from './components/Layout';
import AuthPage from './pages/Auth';
import Dashboard from './pages/Dashboard';
import SalesAnalytics from './pages/SalesAnalytics';
import Forecasting from './pages/Forecasting';
import Segmentation from './pages/Segmentation';
import Recommendations from './pages/Recommendations';
import Sentiment from './pages/Sentiment';
import DataUpload from './pages/DataUpload';
import Settings from './pages/Settings';
import Inventory from './pages/Inventory';
import { AppPage, canAccessPage } from './types';

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState<AppPage>('dashboard');
  const [isDark, setIsDark] = useState(false);
  const resolvedPage: AppPage = canAccessPage(currentPage, user?.role) ? currentPage : 'dashboard';

  const handleNavigate = useCallback((pageId: string) => {
    const nextPage = pageId as AppPage;
    setCurrentPage(canAccessPage(nextPage, user?.role) ? nextPage : 'dashboard');
  }, [user?.role]);

  useEffect(() => {
    if (isAuthenticated && !canAccessPage(currentPage, user?.role)) {
      setCurrentPage('dashboard');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, isAuthenticated, user?.role]);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  if (!isAuthenticated) {
    return <AuthPage />;
  }

  const renderPage = () => {
    switch (resolvedPage) {
      case 'dashboard': return <Dashboard onNavigate={handleNavigate} />;
      case 'sales': return <SalesAnalytics />;
      case 'forecasting': return <Forecasting />;
      case 'segmentation': return <Segmentation />;
      case 'recommendations': return <Recommendations />;
      case 'sentiment': return <Sentiment />;
      case 'inventory': return <Inventory />;
      case 'upload': return <DataUpload />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  return (
    <Layout 
      onNavigate={handleNavigate} 
      currentPage={resolvedPage}
      isDark={isDark}
      onToggleTheme={() => setIsDark(!isDark)}
    >
      {renderPage()}
    </Layout>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <DataProvider>
        <AppContent />
      </DataProvider>
    </AuthProvider>
  );
};

export default App;
