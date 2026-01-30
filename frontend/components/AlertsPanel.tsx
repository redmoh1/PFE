/**
 * AlertsPanel Component
 * 
 * Displays proactive business alerts and recommendations.
 * This is the KEY DIFFERENTIATOR that transforms the dashboard
 * from a passive reporting tool to an active business assistant.
 * 
 * Features:
 * - Severity-based alert styling (critical/warning/info)
 * - Category icons (sales/customer/sentiment/forecast)
 * - Actionable recommendations
 * - Arabic language support in messages
 */

import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  AlertCircle, 
  Info,
  TrendingDown,
  Users,
  MessageSquare,
  Target,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Lightbulb
} from 'lucide-react';

interface BusinessAlert {
  id: string;
  category: string;
  severity: string;
  title: string;
  message: string;
  recommendation: string;
  metric_value?: number;
  threshold?: number;
  icon?: string;
  created_at?: string;
}

interface AlertsData {
  company: string;
  generated_at: string;
  total_alerts: number;
  by_severity: {
    critical: number;
    warning: number;
    info: number;
  };
  by_category: {
    sales: number;
    customer: number;
    sentiment: number;
    forecast: number;
  };
  alerts: BusinessAlert[];
}

const AlertsPanel: React.FC = () => {
  const [alertsData, setAlertsData] = useState<AlertsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/alerts', {
        headers: {
          'X-Company-ID': localStorage.getItem('company') || 'Acme Corp'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch alerts');
      }
      
      const data = await response.json();
      setAlertsData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'bg-red-50 dark:bg-red-900/20',
          border: 'border-red-200 dark:border-red-800',
          icon: 'text-red-500',
          badge: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
        };
      case 'warning':
        return {
          bg: 'bg-amber-50 dark:bg-amber-900/20',
          border: 'border-amber-200 dark:border-amber-800',
          icon: 'text-amber-500',
          badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
        };
      default:
        return {
          bg: 'bg-blue-50 dark:bg-blue-900/20',
          border: 'border-blue-200 dark:border-blue-800',
          icon: 'text-blue-500',
          badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
        };
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'sales':
        return TrendingDown;
      case 'customer':
        return Users;
      case 'sentiment':
        return MessageSquare;
      case 'forecast':
        return Target;
      default:
        return AlertCircle;
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return AlertTriangle;
      case 'warning':
        return AlertCircle;
      default:
        return Info;
    }
  };

  if (isLoading) {
    return (
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <RefreshCw className="animate-spin text-primary" size={20} />
          <span className="text-text-secondary">Loading alerts...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-2xl border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3">
          <AlertTriangle className="text-red-500" size={20} />
          <span className="text-red-700 dark:text-red-300">Failed to load alerts: {error}</span>
          <button 
            onClick={fetchAlerts}
            className="ml-auto text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const hasAlerts = alertsData && alertsData.total_alerts > 0;
  const criticalCount = alertsData?.by_severity?.critical || 0;
  const warningCount = alertsData?.by_severity?.warning || 0;

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      {/* Header */}
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-xl">
            <Lightbulb className="text-primary" size={20} />
          </div>
          <div>
            <h3 className="font-bold text-lg">Business Alerts</h3>
            <p className="text-sm text-text-secondary">
              {hasAlerts 
                ? `${alertsData.total_alerts} items requiring attention`
                : 'No alerts - everything looks good! ✨'
              }
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Severity badges */}
          {criticalCount > 0 && (
            <span className="px-2 py-1 text-xs font-bold rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
              {criticalCount} Critical
            </span>
          )}
          {warningCount > 0 && (
            <span className="px-2 py-1 text-xs font-bold rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300">
              {warningCount} Warning
            </span>
          )}
          
          <button 
            onClick={(e) => { e.stopPropagation(); fetchAlerts(); }}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition"
            title="Refresh alerts"
          >
            <RefreshCw size={16} className="text-text-secondary" />
          </button>
          
          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </div>

      {/* Alert List */}
      {isExpanded && hasAlerts && (
        <div className="border-t border-slate-200 dark:border-slate-700">
          {alertsData.alerts.slice(0, 5).map((alert, index) => {
            const styles = getSeverityStyles(alert.severity);
            const CategoryIcon = getCategoryIcon(alert.category);
            const SeverityIcon = getSeverityIcon(alert.severity);
            
            return (
              <div 
                key={alert.id || index}
                className={`p-4 border-b last:border-b-0 border-slate-100 dark:border-slate-800 ${styles.bg}`}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div className={`mt-0.5 ${styles.icon}`}>
                    <SeverityIcon size={18} />
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-sm">{alert.title}</span>
                      <span className={`px-1.5 py-0.5 text-xs rounded ${styles.badge}`}>
                        {alert.category}
                      </span>
                    </div>
                    
                    <p className="text-sm text-text-secondary dark:text-text-secondaryDark mb-2">
                      {alert.message}
                    </p>
                    
                    {/* Recommendation */}
                    <div className="flex items-start gap-2 p-2 bg-white/50 dark:bg-slate-800/50 rounded-lg">
                      <Lightbulb size={14} className="text-primary mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-text-secondary">
                        <span className="font-medium text-primary">Recommended: </span>
                        {alert.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          
          {alertsData.alerts.length > 5 && (
            <div className="p-3 text-center bg-slate-50 dark:bg-slate-800/50">
              <button className="text-sm text-primary hover:underline">
                View all {alertsData.total_alerts} alerts →
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {isExpanded && !hasAlerts && (
        <div className="p-8 text-center border-t border-slate-200 dark:border-slate-700">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 mb-3">
            <span className="text-2xl">✅</span>
          </div>
          <p className="text-text-secondary">
            All systems healthy. No issues detected.
          </p>
        </div>
      )}
    </div>
  );
};

export default AlertsPanel;
