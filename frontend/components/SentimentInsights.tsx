/**
 * SentimentInsights Component
 * 
 * Displays advanced Arabic-first sentiment analysis with aspect breakdown.
 * This is the KILLER FEATURE for MENA market differentiation.
 * 
 * Features:
 * - Arabic review percentage indicator
 * - Aspect-based sentiment (quality, price, delivery, service, packaging)
 * - Visual progress bars for each aspect
 * - Actionable alerts for problematic aspects
 */

import React, { useState, useEffect } from 'react';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import { useData } from '../store/DataContext';
import { 
  MessageSquare, 
  ThumbsUp, 
  ThumbsDown,
  Globe,
  RefreshCw,
  AlertTriangle,
  Star,
  DollarSign,
  Truck,
  Headphones,
  Package,
  CheckCircle2,
  XCircle
} from 'lucide-react';

// Professional icon mapping for aspects
const ASPECT_ICONS: Record<string, React.ReactNode> = {
  quality: <Star size={18} className="text-amber-500" />,
  price: <DollarSign size={18} className="text-emerald-600" />,
  delivery: <Truck size={18} className="text-blue-600" />,
  service: <Headphones size={18} className="text-violet-600" />,
  packaging: <Package size={18} className="text-slate-600" />,
};

const getAspectIcon = (aspect: string): React.ReactNode => {
  return ASPECT_ICONS[aspect.toLowerCase()] || <CheckCircle2 size={18} className="text-slate-500" />;
};

interface AspectData {
  total_mentions: number;
  positive_pct: number;
  negative_pct: number;
  icon: string;
}

interface SentimentData {
  company: string;
  analysis_date: string;
  total_reviews: number;
  language_distribution: {
    arabic: number;
    english: number;
    arabic_percentage: number;
  };
  sentiment_distribution: {
    positive: number;
    negative: number;
    neutral: number;
    positive_rate: number;
  };
  aspect_analysis: Record<string, AspectData>;
  alerts: Array<{
    aspect: string;
    severity: string;
    message_en: string;
    message_ar: string;
    icon: string;
  }>;
  recommendations: Array<{
    aspect: string;
    message_en: string;
    icon: string;
  }>;
}

const SentimentInsights: React.FC = () => {
  const { user } = useAuth();
  const authFetch = useAuthFetch();
  const { lastTrainingDate } = useData();
  const [data, setData] = useState<SentimentData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasAutoRefreshed, setHasAutoRefreshed] = useState(false);

  useEffect(() => {
    if (!user) return;
    fetchSentiment(true);
  }, [user]);

  // After a successful analytics refresh (e.g., upload), force reanalysis once.
  useEffect(() => {
    if (!user) return;
    if (!lastTrainingDate) return;
    if (hasAutoRefreshed) return;

    setHasAutoRefreshed(true);
    fetchSentiment(true);
  }, [user, lastTrainingDate, hasAutoRefreshed]);

  const fetchSentiment = async (forceRefresh: boolean) => {
    setIsLoading(true);
    setError(null);
    
    try {
      if (!user) {
        setData(null);
        return;
      }

      const url = `/api/advanced-sentiment${forceRefresh ? '?refresh=true' : ''}`;
      const response = await authFetch(url, { cache: 'no-store' });
      
      if (!response.ok) {
        throw new Error('Failed to fetch sentiment data');
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <RefreshCw className="animate-spin text-primary" size={20} />
          <span className="text-text-secondary">Analyzing customer feedback...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3 text-text-secondary">
          <MessageSquare size={20} />
          <span>No sentiment data available. Upload customer reviews to see insights.</span>
        </div>
      </div>
    );
  }

  const positiveRate = data.sentiment_distribution?.positive_rate || 0;
  const arabicPct = data.language_distribution?.arabic_percentage || 0;
  const aspects = data.aspect_analysis || {};

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
              <MessageSquare className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <h3 className="font-bold text-lg">Customer Feedback Intelligence</h3>
              <p className="text-sm text-text-secondary">
                {data.total_reviews} reviews analyzed • Arabic-first NLP
              </p>
            </div>
          </div>
          
          <button 
            onClick={() => fetchSentiment(true)}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition"
            title="Refresh analysis"
          >
            <RefreshCw size={16} className="text-text-secondary" />
          </button>
        </div>

        {/* Overall Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {/* Positive Rate */}
          <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <ThumbsUp size={16} className="text-green-600" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Positive Rate
              </span>
            </div>
            <p className="text-2xl font-bold text-green-600">{positiveRate.toFixed(1)}%</p>
          </div>

          {/* Arabic Content */}
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <Globe size={16} className="text-blue-600" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
                Arabic Reviews
              </span>
            </div>
            <p className="text-2xl font-bold text-blue-600">{arabicPct.toFixed(0)}%</p>
          </div>

          {/* Total Reviews */}
          <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <MessageSquare size={16} className="text-slate-600" />
              <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                Total Reviews
              </span>
            </div>
            <p className="text-2xl font-bold text-slate-700 dark:text-slate-300">{data.total_reviews}</p>
          </div>
        </div>
      </div>

      {/* Aspect Analysis */}
      <div className="p-6">
        <h4 className="font-semibold mb-4 flex items-center gap-2">
          <span>Aspect Breakdown</span>
          <span className="text-xs text-text-secondary font-normal">
            (What customers talk about)
          </span>
        </h4>

        <div className="space-y-4">
          {Object.entries(aspects).map(([aspect, stats]: [string, AspectData]) => {
            const positiveWidth = stats.positive_pct;
            const negativeWidth = stats.negative_pct;
            const neutralWidth = 100 - positiveWidth - negativeWidth;
            const isProblematic = negativeWidth > 40;
            
            return (
              <div key={aspect} className="group">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getAspectIcon(aspect)}
                    <span className="font-medium capitalize">{aspect}</span>
                    {isProblematic && (
                      <AlertTriangle size={14} className="text-amber-500" />
                    )}
                  </div>
                  <div className="text-sm text-text-secondary">
                    {stats.total_mentions} mentions
                  </div>
                </div>
                
                {/* Stacked bar */}
                <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden flex">
                  <div 
                    className="bg-green-500 transition-all"
                    style={{ width: `${positiveWidth}%` }}
                    title={`${positiveWidth.toFixed(0)}% positive`}
                  />
                  <div 
                    className="bg-slate-300 dark:bg-slate-500 transition-all"
                    style={{ width: `${neutralWidth}%` }}
                    title={`${neutralWidth.toFixed(0)}% neutral`}
                  />
                  <div 
                    className="bg-red-500 transition-all"
                    style={{ width: `${negativeWidth}%` }}
                    title={`${negativeWidth.toFixed(0)}% negative`}
                  />
                </div>
                
                {/* Labels */}
                <div className="flex justify-between text-xs text-text-secondary mt-1">
                  <span className="text-green-600">{positiveWidth.toFixed(0)}% positive</span>
                  <span className="text-red-600">{negativeWidth.toFixed(0)}% negative</span>
                </div>
              </div>
            );
          })}
        </div>

        {Object.keys(aspects).length === 0 && (
          <p className="text-center text-text-secondary py-4">
            No aspect data available. Ensure reviews contain feedback about quality, price, delivery, or service.
          </p>
        )}
      </div>

      {/* Alerts Section */}
      {data.alerts && data.alerts.length > 0 && (
        <div className="px-6 pb-6">
          <h4 className="font-semibold mb-3 text-amber-600 dark:text-amber-400 flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>Issues Detected</span>
          </h4>
          
          <div className="space-y-2">
            {data.alerts.map((alert, idx) => (
              <div 
                key={idx}
                className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg"
              >
                <div className="flex items-center gap-2 mb-1">
                  {getAspectIcon(alert.aspect)}
                  <span className="font-medium text-amber-700 dark:text-amber-300">
                    {alert.message_en}
                  </span>
                </div>
                <p className="text-sm text-amber-600 dark:text-amber-400 text-right" dir="rtl">
                  {alert.message_ar}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths Section */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="px-6 pb-6">
          <h4 className="font-semibold mb-3 text-green-600 dark:text-green-400 flex items-center gap-2">
            <ThumbsUp size={16} />
            <span>Strengths</span>
          </h4>
          
          <div className="space-y-2">
            {data.recommendations.map((rec, idx) => (
              <div 
                key={idx}
                className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  {getAspectIcon(rec.aspect)}
                  <span className="font-medium text-green-700 dark:text-green-300">
                    {rec.message_en}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SentimentInsights;
