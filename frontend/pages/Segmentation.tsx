
import React, { useEffect, useState } from 'react';
import { useData } from '../store/DataContext';
import { useAuth } from '../store/AuthContext';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Upload } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

interface SegmentationMetadata {
  total_customers: number;
  segments: any[];
  last_calculated: string | null;
  data_source: string;
  model_version: string;
}

const Segmentation: React.FC = () => {
  const { segments } = useData();
  const { user } = useAuth();
  const [metadata, setMetadata] = useState<SegmentationMetadata | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetadata = async () => {
      if (!user) return;
      try {
        const headers = { 'X-Company-ID': user.company };
        const res = await fetch(`${API_BASE}/api/segmentation`, { headers });
        if (res.status === 204) {
          setMetadata(null);
        } else if (res.ok) {
          const data = await res.json();
          setMetadata(data);
        }
      } catch (e) {
        console.error('Failed to fetch segmentation metadata:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchMetadata();
  }, [user]);

  const hasData = segments && segments.length > 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-2xl font-bold tracking-tight">RFM Segmentation</h2>
        <p className="text-text-secondary">Classifying customers based on Recency, Frequency, and Monetary value.</p>
        {metadata && (
          <div className="mt-2 text-xs text-text-secondary flex gap-4">
            <span>Source: {metadata.data_source}</span>
            <span>Total Customers: {metadata.total_customers}</span>
            {metadata.last_calculated && (
              <span>Last Calculated: {new Date(metadata.last_calculated).toLocaleDateString()}</span>
            )}
          </div>
        )}
      </div>

      {!hasData && !loading ? (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-2xl p-12 text-center">
          <div className="flex items-center justify-center mb-4 text-amber-600">
            <Upload size={32} />
          </div>
          <h3 className="text-lg font-bold text-amber-900 dark:text-amber-100 mb-2">No Segmentation Data Available</h3>
          <p className="text-amber-800 dark:text-amber-200 mb-4">
            RFM segmentation will be calculated and displayed here once you upload sales data.
          </p>
          <p className="text-sm text-amber-700 dark:text-amber-300">
            Upload a CSV with OrderID, OrderDate, TotalPrice, ProductID, and City columns to generate customer segments.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col items-center">
            <h3 className="text-lg font-bold mb-6 w-full">Cohort Distribution</h3>
            <div className="h-[400px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={segments}
                    cx="50%"
                    cy="50%"
                    innerRadius={80}
                    outerRadius={140}
                    paddingAngle={5}
                    dataKey="count"
                  >
                    {segments.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend layout="horizontal" verticalAlign="bottom" align="center" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
            <h3 className="text-lg font-bold mb-6">Cohort Insights & Strategy</h3>
            <div className="flex-1 space-y-4">
              {segments.map((segment, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 transition-colors">
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: segment.color }} />
                      <span className="font-bold">{segment.name}</span>
                    </div>
                    <span className="text-xs font-semibold bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-text-secondary">
                      {segment.count} customers
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {getStrategyForSegment(segment.name)}
                  </p>
                  {segment.recency !== undefined && (
                    <div className="mt-2 flex gap-4 text-xs text-text-secondary">
                      <span>Recency: {segment.recency?.toFixed(1)}</span>
                      <span>Frequency: {segment.frequency?.toFixed(1)}</span>
                      <span>Monetary: ${segment.monetary?.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function getStrategyForSegment(name: string) {
  switch (name) {
    case 'Champions': return 'Reward them. Can be early adopters for new products. Promote most expensive items.';
    case 'Loyal': return 'Upsell higher value products. Engage in loyalty programs. Ask for reviews.';
    case 'Potential Loyalists': return 'Offer membership / loyalty program. Recommend relevant products.';
    case 'At Risk': return 'Send personalized emails to reconnect. Offer limited-time discounts / renewals.';
    case 'Hibernating': return 'Re-engage with significant discounts. Share "What\'s New" updates.';
    case 'Need Attention': return 'Win back with special offers. Highlight value proposition.';
    case 'Lost': return 'Reactivation campaign with strong incentives.';
    default: return 'Standard marketing approach.';
  }
}

export default Segmentation;
