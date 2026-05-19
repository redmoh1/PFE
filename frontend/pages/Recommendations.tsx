
import React, { useEffect, useState } from 'react';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import { Info, Lightbulb, Loader2, ShoppingCart, Percent, Zap, Upload } from 'lucide-react';

interface Recommendation {
  if_product: string;
  then_product: string;
  confidence: number;
  lift: number;
}

const Recommendations: React.FC = () => {
  const { user, selectedBranchId } = useAuth();
  const authFetch = useAuthFetch();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRecommendations = async () => {
      if (!user) {
        setLoading(false);
        return;
      }
      try {
        const params = new URLSearchParams({ limit: '10' });
        if (selectedBranchId) params.set('branch_id', selectedBranchId);
        const res = await authFetch(`/api/recommendations?${params.toString()}`);
        if (res.status === 204) {
          setRecommendations([]);
        } else if (res.ok) {
          const data = await res.json();
          setRecommendations(data);
        } else {
          console.warn('Recommendations API returned non-OK status:', res.status);
          setRecommendations([]);
        }
      } catch (e) {
        console.error('Failed to fetch recommendations:', e);
        setRecommendations([]);
      } finally {
        setLoading(false);
      }
    };
    fetchRecommendations();
  }, [user, selectedBranchId, authFetch]);

  const hasData = recommendations && recommendations.length > 0;
  const avgConfidence = hasData 
    ? (recommendations.reduce((sum, r) => sum + r.confidence, 0) / recommendations.length * 100).toFixed(0)
    : 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-2xl font-bold tracking-tight">Market Basket Analysis</h2>
        <p className="text-text-secondary">Next-best-product recommendations using the Apriori algorithm.</p>
        <div className="mt-2 flex items-start gap-2 text-xs text-text-secondary dark:text-text-secondaryDark max-w-2xl">
          <Info size={14} className="mt-0.5 text-primary/80" />
          <p>Rules are learned from product co-occurrence in transactions; confidence and lift quantify recommendation strength beyond chance.</p>
        </div>
        {hasData && (
          <div className="mt-2 text-xs text-text-secondary">
            Source: product_recommendations.csv | Total Rules: {recommendations.length}
          </div>
        )}
      </div>

      {loading && !hasData ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={40} className="animate-spin text-primary" />
        </div>
      ) : !hasData ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-2xl p-12 text-center">
          <div className="flex items-center justify-center mb-4 text-green-600">
            <Upload size={32} />
          </div>
          <h3 className="text-lg font-bold text-green-900 dark:text-green-100 mb-2">No Recommendation Rules Generated</h3>
          <p className="text-green-800 dark:text-green-200 mb-4">
            Market basket analysis recommendations will be displayed here once you upload transaction data and generate association rules.
          </p>
          <p className="text-sm text-green-700 dark:text-green-300">
            Upload sales transaction data with OrderID, ProductID, and OrderDate to discover product associations.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-primary/5 p-6 rounded-2xl border border-primary/10">
              <Zap className="text-primary mb-3" size={24} />
              <h4 className="font-bold text-sm text-primary uppercase tracking-wider mb-1">Total Rules</h4>
              <p className="text-3xl font-bold">{recommendations.length}</p>
            </div>
            <div className="bg-success/5 p-6 rounded-2xl border border-success/10">
              <Percent className="text-success mb-3" size={24} />
              <h4 className="font-bold text-sm text-success uppercase tracking-wider mb-1">Avg Confidence</h4>
              <p className="text-3xl font-bold">{avgConfidence}%</p>
            </div>
          </div>

          {hasData && (
            <div className="grid grid-cols-1 gap-6">
              {recommendations.map((rec, idx) => (
                <div key={idx} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-center gap-8 hover:border-primary/50 transition-colors">
                  <div className="flex-1 flex items-center justify-between w-full md:w-auto">
                    <div className="flex flex-col items-center gap-2 p-4 bg-slate-50 dark:bg-slate-900 rounded-xl flex-1 text-center">
                      <span className="text-xs font-bold text-text-secondary uppercase">Base Product</span>
                      <span className="font-bold">{rec.if_product}</span>
                    </div>
                    <div className="mx-6 text-slate-300">
                      <Zap size={32} fill="currentColor" />
                    </div>
                    <div className="flex flex-col items-center gap-2 p-4 bg-primary/5 rounded-xl flex-1 text-center border border-primary/10">
                      <span className="text-xs font-bold text-primary uppercase">Recommended</span>
                      <span className="font-bold text-primary">{rec.then_product}</span>
                    </div>
                  </div>

                  <div className="flex gap-8 border-l border-slate-100 dark:border-slate-800 pl-8 h-full items-center">
                    <div>
                      <p className="text-xs text-text-secondary font-semibold uppercase">Confidence</p>
                      <p className="text-2xl font-bold">{(rec.confidence * 100).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary font-semibold uppercase">Lift Score</p>
                      <p className="text-2xl font-bold">{rec.lift.toFixed(2)}x</p>
                    </div>
                    <button className="bg-primary text-white p-3 rounded-xl hover:bg-primary/90 transition-all">
                      <ShoppingCart size={20} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {hasData && recommendations.length > 0 && (
            <div className="bg-card-light dark:bg-card-dark p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Lightbulb className="text-warning" />
                Cross-Sell Opportunity Detected
              </h3>
              <p className="text-text-secondary leading-relaxed">
                The association rule between <strong>{recommendations[0]?.if_product}</strong> and <strong>{recommendations[0]?.then_product}</strong> is strong. 
                Customers purchasing the base product are <strong>{recommendations[0]?.lift.toFixed(2)} times</strong> more likely to purchase the recommended product than a random customer. 
                We suggest bundling these in your next marketing campaign.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Recommendations;
