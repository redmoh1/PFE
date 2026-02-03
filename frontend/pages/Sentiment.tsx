
import React, { useEffect, useState } from 'react';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import { Smile, Meh, Frown, MessageCircle, Upload, Globe, Brain, Info, Loader2, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE || '';

interface SentimentAnalysis {
  total_reviews: number;
  sentiment_breakdown: Array<{
    label: string;
    count: number;
    percentage: number;
  }>;
  top_keywords: string[];
  last_analyzed: string | null;
  data_source: string;
  model_info?: {
    model_type: string;
    supports_arabic: boolean;
    avg_confidence: number;
  };
  language_breakdown?: Array<{
    language: string;
    count: number;
    percentage: number;
  }>;
}

const Sentiment: React.FC = () => {
  const { user } = useAuth();
  const authFetch = useAuthFetch();
  const [sentiment, setSentiment] = useState<SentimentAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  const fetchSentimentAnalysis = async () => {
    if (!user) {
      setLoading(false);
      return;
    }
    try {
      const res = await authFetch('/api/sentiment');
      if (res.status === 204) {
        setSentiment(null);
      } else if (res.ok) {
        const data = await res.json();
        setSentiment(data.data || data);
      } else {
        console.warn('Sentiment API returned non-OK status:', res.status);
        setSentiment(null);
      }
    } catch (e) {
      console.error('Failed to fetch sentiment analysis:', e);
      setSentiment(null);
    } finally {
      setLoading(false);
    }
  };

  const runNewAnalysis = async () => {
    if (!user) return;
    setAnalyzing(true);
    try {
      const res = await authFetch('/api/sentiment/analyze', {
        method: 'POST'
      });
      if (res.ok) {
        // Refresh data after analysis
        await fetchSentimentAnalysis();
      }
    } catch (e) {
      console.error('Failed to run sentiment analysis:', e);
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    fetchSentimentAnalysis();
  }, [user]);

  const getIcon = (label: string) => {
    switch (label) {
      case 'Positive': return <Smile className="text-success" size={24} />;
      case 'Neutral': return <Meh className="text-warning" size={24} />;
      case 'Negative': return <Frown className="text-error" size={24} />;
      default: return null;
    }
  };

  const getBg = (label: string) => {
    switch (label) {
      case 'Positive': return 'bg-success/10';
      case 'Neutral': return 'bg-warning/10';
      case 'Negative': return 'bg-error/10';
      default: return 'bg-slate-100';
    }
  };

  const hasData = sentiment && sentiment.total_reviews > 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Customer Sentiment</h2>
            <p className="text-text-secondary">NLP-based analysis of customer reviews and feedback surveys.</p>
            <div className="mt-2 flex items-start gap-2 text-xs text-text-secondary dark:text-text-secondaryDark max-w-2xl">
              <Info size={14} className="mt-0.5 text-primary/80" />
              <p>Sentiment labels are inferred from review text patterns; keyword lists highlight recurring themes across feedback.</p>
            </div>
          </div>
          <button
            onClick={runNewAnalysis}
            disabled={analyzing || loading}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {analyzing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            {analyzing ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>
        {sentiment && (
          <div className="mt-3 flex flex-wrap gap-4 text-xs">
            <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">
              Source: {sentiment.data_source}
            </span>
            <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">
              Total Reviews: {sentiment.total_reviews}
            </span>
            {sentiment.model_info && (
              <>
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full flex items-center gap-1">
                  <Brain size={12} />
                  {sentiment.model_info.model_type}
                </span>
                {sentiment.model_info.supports_arabic && (
                  <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full flex items-center gap-1">
                    <Globe size={12} />
                    Arabic Enabled
                  </span>
                )}
                <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
                  Avg Confidence: {(sentiment.model_info.avg_confidence * 100).toFixed(1)}%
                </span>
              </>
            )}
            {sentiment.last_analyzed && (
              <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">
                Last Analyzed: {new Date(sentiment.last_analyzed).toLocaleDateString()}
              </span>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={40} className="animate-spin text-primary" />
        </div>
      ) : !hasData ? (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl p-12 text-center">
          <div className="flex items-center justify-center mb-4 text-blue-600">
            <Upload size={32} />
          </div>
          <h3 className="text-lg font-bold text-blue-900 dark:text-blue-100 mb-2">No Sentiment Data Available</h3>
          <p className="text-blue-800 dark:text-blue-200 mb-4">
            Customer sentiment analysis will be displayed here once you upload review data.
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Upload a CSV with ReviewText or similar column to analyze customer feedback sentiment.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {sentiment?.sentiment_breakdown.map((item, idx) => (
              <div key={idx} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="flex justify-between items-start mb-6">
                  <div className={`p-3 rounded-xl ${getBg(item.label)}`}>
                    {getIcon(item.label)}
                  </div>
                  <span className="text-xs font-bold text-text-secondary uppercase tracking-widest">Sentiment</span>
                </div>
                <h4 className="text-sm font-semibold text-text-secondary mb-1">{item.label} Feedback</h4>
                <p className="text-3xl font-bold">{item.percentage.toFixed(1)}%</p>
                <p className="text-xs text-text-secondary mt-1">{item.count} reviews</p>
                <div className="mt-4 h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-1000 ${item.label === 'Positive' ? 'bg-success' : item.label === 'Neutral' ? 'bg-warning' : 'bg-error'}`} 
                    style={{ width: `${item.percentage}%` }} 
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <h3 className="text-lg font-bold mb-6">Sentiment Distribution</h3>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sentiment?.sentiment_breakdown || []}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="label" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip />
                    <Bar dataKey="percentage" radius={[4, 4, 0, 0]} barSize={60}>
                      {sentiment?.sentiment_breakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.label === 'Positive' ? '#22C55E' : entry.label === 'Neutral' ? '#F59E0B' : '#EF4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                <MessageCircle size={20} className="text-primary" />
                Top Keywords
              </h3>
              <div className="space-y-3">
                {sentiment && sentiment.top_keywords.length > 0 ? (
                  sentiment.top_keywords.map((keyword, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                      <span className="text-sm font-medium capitalize">{keyword}</span>
                      <span className="text-xs font-bold px-2 py-1 rounded-full bg-primary/10 text-primary">
                        Frequent
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-text-secondary text-center py-4">No keywords extracted</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Sentiment;
