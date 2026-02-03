
import React, { useState, useEffect } from 'react';
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

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isDark, setIsDark] = useState(false);

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
    switch (currentPage) {
      case 'dashboard': return <Dashboard onNavigate={setCurrentPage} />;
      case 'sales': return <SalesAnalytics />;
      case 'forecasting': return <Forecasting />;
      case 'segmentation': return <Segmentation />;
      case 'recommendations': return <Recommendations />;
      case 'sentiment': return <Sentiment />;
      case 'upload': return <DataUpload />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  return (
    <Layout 
      onNavigate={setCurrentPage} 
      currentPage={currentPage}
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
