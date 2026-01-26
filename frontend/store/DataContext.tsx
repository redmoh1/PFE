
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { SalesData, ForecastPoint, RFMSegment, Recommendation, SentimentData, KPIData } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface DataContextType {
  sales: SalesData[];
  forecast: ForecastPoint[];
  segments: RFMSegment[];
  recommendations: Recommendation[];
  sentiment: SentimentData[];
  kpis: KPIData | null;
  lastTrainingDate: string | null;
  isProcessing: boolean;
  isLoading: boolean;
  error: string | null;
  uploadData: (type: string, data: any[]) => void;
  refreshData: () => Promise<void>;
  resetAllAnalytics: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [sales, setSales] = useState<SalesData[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [segments, setSegments] = useState<RFMSegment[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [sentiment, setSentiment] = useState<SentimentData[]>([]);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [lastTrainingDate, setLastTrainingDate] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    if (!user) {
      setSales([]);
      setForecast([]);
      setSegments([]);
      setRecommendations([]);
      setSentiment([]);
      setLastTrainingDate(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Company-ID': user.company || 'demo-company'
    };

    try {
      // Fetch KPIs
      try {
        const kpiRes = await fetch(`${API_BASE_URL}/api/kpis`, { headers });
        if (kpiRes.ok) {
          const kpiData = await kpiRes.json();
          setKpis(kpiData);
        }
      } catch (e) {
        console.error('Failed to fetch KPIs:', e);
      }

      // Fetch sales data (raw data endpoint)
      try {
        const salesRes = await fetch(`${API_BASE_URL}/api/raw-data?limit=100`, { headers });
        if (salesRes.ok) {
          const salesData = await salesRes.json();
          setSales(salesData.map((item: any, idx: number) => ({
            id: item.OrderID || item.Product_ID || `s-${idx}`,
            date: item.OrderDate || item.Sale_Date || item.Date || new Date().toISOString().split('T')[0],
            amount: item.TotalPrice || item.Sales_Amount || 0,
            product: item.ProductID || item.Product_ID || 'Unknown',
            category: 'Product',
            city: item.City || item.Region || 'Unknown',
            customerId: item.CustomerID || 'c-unknown'
          })));
        }
      } catch (e) {
        console.error('Failed to fetch sales data:', e);
      }

      // Fetch forecast data
      try {
        const forecastRes = await fetch(`${API_BASE_URL}/api/monthly-sales`, { headers });
        if (forecastRes.ok) {
          const forecastData = await forecastRes.json();
          setForecast(forecastData.map((item: any) => ({
            date: item.month,
            actual: item.actual_sales || undefined,
            forecast: item.forecasted_sales || undefined
          })));
        }
      } catch (e) {
        console.error('Failed to fetch forecast data:', e);
      }

      // Fetch recommendations
      try {
        const recsRes = await fetch(`${API_BASE_URL}/api/recommendations?limit=10`, { headers });
        if (recsRes.status === 204) {
          setRecommendations([]);
        } else if (recsRes.ok) {
          const recsData = await recsRes.json();
          setRecommendations(recsData.map((item: any, idx: number) => ({
            id: `rec-${idx}`,
            baseProduct: item.if_product || '',
            recommendedProduct: item.then_product || '',
            confidence: item.confidence || 0,
            lift: item.lift || 0
          })));
        } else {
          console.warn('Recommendations API returned non-OK status:', recsRes.status);
          setRecommendations([]);
        }
      } catch (e) {
        console.error('Failed to fetch recommendations:', e);
        setRecommendations([]);
      }

      // Fetch RFM segmentation data (real data from rfm_table.csv)
      try {
        const segmentRes = await fetch(`${API_BASE_URL}/api/segmentation`, { headers });
        if (segmentRes.status === 204) {
          setSegments([]);
        } else if (segmentRes.ok) {
          const segmentData = await segmentRes.json();
          if (segmentData.segments && segmentData.segments.length > 0) {
            setSegments(segmentData.segments.map((item: any) => ({
              name: item.segment,
              count: item.customer_count,
              color: item.color,
              recency: item.avg_recency,
              frequency: item.avg_frequency,
              monetary: item.avg_monetary
            })));
          } else {
            setSegments([]);
          }
        } else {
          console.warn('Segmentation API returned non-OK status:', segmentRes.status);
          setSegments([]);
        }
      } catch (e) {
        console.error('Failed to fetch segmentation:', e);
        setSegments([]);
      }

      setLastTrainingDate(new Date().toISOString());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to load data from server: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Reset all analytics state - used after dataset deletion
  const resetAllAnalytics = () => {
    setSales([]);
    setForecast([]);
    setSegments([]);
    setRecommendations([]);
    setSentiment([]);
    setKpis(null);
    setLastTrainingDate(null);
    setError(null);
    
    // Clear local storage for this tenant
    if (user) {
      const tenantKey = `data_${user.company}`;
      localStorage.removeItem(tenantKey);
    }
  };

  // Load user-specific data from local storage to simulate tenant isolation
  useEffect(() => {
    fetchData();
  }, [user]);

  const uploadData = async (type: string, data: any[]) => {
    setIsProcessing(true);
    // Simulate pipeline processing (cleaning, FE, ML training)
    setTimeout(() => {
      if (type === 'sales') setSales(data as SalesData[]);
      setLastTrainingDate(new Date().toISOString());
      setIsProcessing(false);
      
      // Save updated data
      if (user) {
        const tenantKey = `data_${user.company}`;
        localStorage.setItem(tenantKey, JSON.stringify({
          sales: type === 'sales' ? data : sales,
          forecast,
          segments,
          recommendations,
          sentiment,
          lastTrainingDate: new Date().toISOString()
        }));
      }
    }, 2000);
  };

  return (
    <DataContext.Provider value={{
      sales, forecast, segments, recommendations, sentiment, 
      kpis,
      lastTrainingDate, isProcessing, isLoading, error,
      uploadData, refreshData: fetchData, resetAllAnalytics
    }}>
      {children}
    </DataContext.Provider>
  );
};

export const useData = () => {
  const context = useContext(DataContext);
  if (!context) throw new Error('useData must be used within DataProvider');
  return context;
};
