
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth, useAuthFetch } from './AuthContext';
import {
  SalesData,
  ForecastPoint,
  RFMSegment,
  Recommendation,
  SentimentData,
  KPIData,
  DecisionInsight,
  DataQualityReport,
  AnalyticsFilters,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE || '';

interface DataContextType {
  sales: SalesData[];
  forecast: ForecastPoint[];
  segments: RFMSegment[];
  recommendations: Recommendation[];
  sentiment: SentimentData[];
  kpis: KPIData | null;
  insights: DecisionInsight[];
  dataQuality: DataQualityReport | null;
  filters: AnalyticsFilters;
  setFilters: (next: Partial<AnalyticsFilters>) => void;
  clearFilters: () => void;
  cityOptions: string[];
  productOptions: string[];
  lastTrainingDate: string | null;
  isProcessing: boolean;
  isLoading: boolean;
  error: string | null;
  uploadData: (type: string, data: any[]) => void;
  refreshData: () => Promise<void>;
  resetAllAnalytics: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

// Helper to get auth token for fetch
const getAuthHeaders = (token: string | null | undefined, companyId: string | null | undefined): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (companyId) {
    headers['X-Company-ID'] = companyId;
  }
  return headers;
};

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token } = useAuth();
  const authFetch = useAuthFetch();
  const [sales, setSales] = useState<SalesData[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [segments, setSegments] = useState<RFMSegment[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [sentiment, setSentiment] = useState<SentimentData[]>([]);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [insights, setInsights] = useState<DecisionInsight[]>([]);
  const [dataQuality, setDataQuality] = useState<DataQualityReport | null>(null);
  const [filters, setFiltersState] = useState<AnalyticsFilters>({
    startDate: '',
    endDate: '',
    city: '',
    product: '',
    comparePrevious: false,
  });
  const [cityOptions, setCityOptions] = useState<string[]>([]);
  const [productOptions, setProductOptions] = useState<string[]>([]);
  const [lastTrainingDate, setLastTrainingDate] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const setFilters = useCallback((next: Partial<AnalyticsFilters>) => {
    setFiltersState(prev => ({ ...prev, ...next }));
  }, []);

  const clearFilters = useCallback(() => {
    setFiltersState({
      startDate: '',
      endDate: '',
      city: '',
      product: '',
      comparePrevious: false,
    });
  }, []);

  const buildAnalyticsQuery = useCallback((
    base: Partial<AnalyticsFilters> = {},
    opts: { includeCityProduct?: boolean } = {}
  ) => {
    const includeCityProduct = opts.includeCityProduct ?? true;
    const params = new URLSearchParams();

    const merged: AnalyticsFilters = {
      ...filters,
      ...base,
    } as AnalyticsFilters;

    if (merged.startDate) params.set('start_date', merged.startDate);
    if (merged.endDate) params.set('end_date', merged.endDate);
    if (includeCityProduct) {
      if (merged.city) params.set('city', merged.city);
      if (merged.product) params.set('product', merged.product);
    }
    return params;
  }, [filters]);

  const computePreviousRange = useCallback((startDate: string, endDate: string) => {
    // Mirrors backend logic: period_length = (end - start).days
    const start = new Date(`${startDate}T00:00:00Z`);
    const end = new Date(`${endDate}T00:00:00Z`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
    const msPerDay = 24 * 60 * 60 * 1000;
    const periodLengthDays = Math.floor((end.getTime() - start.getTime()) / msPerDay);
    const prevEnd = new Date(start.getTime() - msPerDay);
    const prevStart = new Date(prevEnd.getTime() - periodLengthDays * msPerDay);

    const toYmd = (d: Date) => d.toISOString().slice(0, 10);
    return { startDate: toYmd(prevStart), endDate: toYmd(prevEnd) };
  }, []);

  /**
   * CRITICAL: Fetch ALL data fresh from the server with JWT authentication.
   * 
   * This function:
   * 1. Clears all local state FIRST to prevent stale data display
   * 2. Fetches fresh data from each endpoint using JWT auth
   * 3. Handles 204 (No Content) responses by setting empty arrays
   * 4. NEVER uses cached or localStorage data for analytics
   */
  const fetchData = useCallback(async () => {
    if (!user) {
      // Clear all state when no user
      setSales([]);
      setForecast([]);
      setSegments([]);
      setRecommendations([]);
      setSentiment([]);
      setKpis(null);
      setInsights([]);
      setDataQuality(null);
      setCityOptions([]);
      setProductOptions([]);
      setLastTrainingDate(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    const headers = getAuthHeaders(token, user.company);
    const fetchOpts: RequestInit = { headers, cache: 'no-store' };

    const analyticsParams = buildAnalyticsQuery();
    const analyticsQs = analyticsParams.toString();
    const analyticsSuffix = analyticsQs ? `?${analyticsQs}` : '';

    const dateOnlyParams = buildAnalyticsQuery({}, { includeCityProduct: false });
    const dateOnlyQs = dateOnlyParams.toString();
    const dateOnlySuffix = dateOnlyQs ? `?${dateOnlyQs}` : '';

    try {
      // Fetch KPIs
      try {
        const kpiRes = await fetch(`${API_BASE_URL}/api/kpis${analyticsSuffix}`, fetchOpts);
        if (kpiRes.status === 204) {
          setKpis(null);
        } else if (kpiRes.ok) {
          const kpiData = await kpiRes.json();
          // Handle standardized response format
          setKpis(kpiData.data || kpiData);
        } else {
          setKpis(null);
        }
      } catch (e) {
        console.error('Failed to fetch KPIs:', e);
        setKpis(null);
      }

      // Fetch filter options (date-scoped, not city/product scoped)
      try {
        const citiesRes = await fetch(`${API_BASE_URL}/api/top-cities${dateOnlySuffix ? `${dateOnlySuffix}&limit=50` : '?limit=50'}`, fetchOpts);
        if (citiesRes.ok) {
          const payload = await citiesRes.json();
          const data = payload?.data || payload;
          const options = (Array.isArray(data) ? data : []).map((c: any) => String(c.city)).filter(Boolean);
          setCityOptions(options);
        } else {
          setCityOptions([]);
        }
      } catch (e) {
        console.error('Failed to fetch city options:', e);
        setCityOptions([]);
      }

      try {
        const productsRes = await fetch(`${API_BASE_URL}/api/top-products${dateOnlySuffix ? `${dateOnlySuffix}&limit=50` : '?limit=50'}`, fetchOpts);
        if (productsRes.ok) {
          const payload = await productsRes.json();
          const data = payload?.data || payload;
          const options = (Array.isArray(data) ? data : []).map((p: any) => String(p.product_id)).filter(Boolean);
          setProductOptions(options);
        } else {
          setProductOptions([]);
        }
      } catch (e) {
        console.error('Failed to fetch product options:', e);
        setProductOptions([]);
      }

      // Fetch sales data (raw data endpoint)
      try {
        const salesParams = buildAnalyticsQuery();
        salesParams.set('limit', '100');
        const salesRes = await fetch(`${API_BASE_URL}/api/raw-data?${salesParams.toString()}`, fetchOpts);
        if (salesRes.status === 204) {
          setSales([]);
        } else if (salesRes.ok) {
          const salesResponse = await salesRes.json();
          const salesData = salesResponse.data || salesResponse;
          setSales(salesData.map((item: any, idx: number) => ({
            id: item.OrderID || item.Product_ID || `s-${idx}`,
            date: item.OrderDate || item.Sale_Date || item.Date || new Date().toISOString().split('T')[0],
            amount: item.TotalPrice || item.Sales_Amount || 0,
            product: item.ProductID || item.Product_ID || 'Unknown',
            category: 'Product',
            city: item.City || item.Region || 'Unknown',
            customerId: item.CustomerID || 'c-unknown'
          })));
        } else {
          setSales([]);
        }
      } catch (e) {
        console.error('Failed to fetch sales data:', e);
        setSales([]);
      }

      // Fetch forecast data
      try {
        const forecastRes = await fetch(`${API_BASE_URL}/api/monthly-sales${analyticsSuffix}`, fetchOpts);
        if (forecastRes.status === 204) {
          setForecast([]);
        } else if (forecastRes.ok) {
          const forecastResponse = await forecastRes.json();
          const forecastData = forecastResponse.data || forecastResponse;
          const currentPoints: ForecastPoint[] = (Array.isArray(forecastData) ? forecastData : []).map((item: any) => ({
            date: item.month || item.date,
            actual: item.actual_sales ?? item.actual ?? undefined,
            forecast: item.forecasted_sales ?? item.forecast ?? undefined,
            forecast_upper: item.forecast_upper || undefined,
            forecast_lower: item.forecast_lower || undefined,
          }));

          if (filters.comparePrevious && filters.startDate && filters.endDate) {
            const prev = computePreviousRange(filters.startDate, filters.endDate);
            if (prev) {
              const prevParams = buildAnalyticsQuery(
                { startDate: prev.startDate, endDate: prev.endDate },
                { includeCityProduct: true }
              );
              const prevRes = await fetch(`${API_BASE_URL}/api/monthly-sales?${prevParams.toString()}`, fetchOpts);
              if (prevRes.ok && prevRes.status !== 204) {
                const prevPayload = await prevRes.json();
                const prevData = prevPayload?.data || prevPayload;
                const prevPoints: ForecastPoint[] = (Array.isArray(prevData) ? prevData : []).map((item: any) => ({
                  date: item.month || item.date,
                  actual: item.actual_sales ?? item.actual ?? undefined,
                  forecast: item.forecasted_sales ?? item.forecast ?? undefined,
                }));
                const prevMap = new Map<string, ForecastPoint>();
                prevPoints.forEach(p => prevMap.set(p.date, p));

                const merged = currentPoints.map(p => {
                  const prevPoint = prevMap.get(p.date);
                  return {
                    ...p,
                    previous_actual: prevPoint?.actual,
                    previous_forecast: prevPoint?.forecast,
                  };
                });
                setForecast(merged);
              } else {
                setForecast(currentPoints);
              }
            } else {
              setForecast(currentPoints);
            }
          } else {
            setForecast(currentPoints);
          }
        } else {
          setForecast([]);
        }
      } catch (e) {
        console.error('Failed to fetch forecast data:', e);
        setForecast([]);
      }

      // Fetch recommendations - ALWAYS fresh from server with JWT auth
      try {
        const recsRes = await fetch(`${API_BASE_URL}/api/recommendations?limit=10`, fetchOpts);
        if (recsRes.status === 204) {
          console.log('[DataContext] Recommendations API returned 204 - clearing state');
          setRecommendations([]);
        } else if (recsRes.ok) {
          const recsResponse = await recsRes.json();
          const recsData = recsResponse.data || recsResponse;
          if (Array.isArray(recsData) && recsData.length > 0) {
            setRecommendations(recsData.map((item: any, idx: number) => ({
              id: `rec-${idx}`,
              baseProduct: item.if_product || '',
              recommendedProduct: item.then_product || '',
              confidence: item.confidence || 0,
              lift: item.lift || 0
            })));
          } else {
            setRecommendations([]);
          }
        } else {
          console.warn('Recommendations API returned non-OK status:', recsRes.status);
          setRecommendations([]);
        }
      } catch (e) {
        console.error('Failed to fetch recommendations:', e);
        setRecommendations([]);
      }

      // Fetch RFM segmentation data - ALWAYS fresh from server with JWT auth
      try {
        const segmentRes = await fetch(`${API_BASE_URL}/api/segmentation`, fetchOpts);
        if (segmentRes.status === 204) {
          console.log('[DataContext] Segmentation API returned 204 - clearing state');
          setSegments([]);
        } else if (segmentRes.ok) {
          const segmentResponse = await segmentRes.json();
          const segmentData = segmentResponse.data || segmentResponse;
          const segmentsArr = segmentData.segments || segmentData;
          if (Array.isArray(segmentsArr) && segmentsArr.length > 0) {
            setSegments(segmentsArr.map((item: any) => ({
              name: item.segment || item.name,
              count: item.customer_count || item.count,
              color: item.color,
              recency: item.avg_recency || item.recency,
              frequency: item.avg_frequency || item.frequency,
              monetary: item.avg_monetary || item.monetary
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

      // Fetch Decision Insights (rule-based)
      try {
        const insightsParams = buildAnalyticsQuery();
        insightsParams.set('limit', '8');
        const insightsRes = await fetch(`${API_BASE_URL}/api/insights?${insightsParams.toString()}`, fetchOpts);
        if (insightsRes.status === 204) {
          setInsights([]);
        } else if (insightsRes.ok) {
          const payload = await insightsRes.json();
          const items = payload?.insights || payload?.data || [];
          setInsights(Array.isArray(items) ? items : []);
        } else {
          setInsights([]);
        }
      } catch (e) {
        console.error('Failed to fetch insights:', e);
        setInsights([]);
      }

      // Fetch Data Quality Report
      try {
        const dqRes = await fetch(`${API_BASE_URL}/api/data-quality`, fetchOpts);
        if (dqRes.status === 204) {
          setDataQuality(null);
        } else if (dqRes.ok) {
          const payload = await dqRes.json();
          setDataQuality(payload?.data || payload);
        } else {
          setDataQuality(null);
        }
      } catch (e) {
        console.error('Failed to fetch data quality report:', e);
        setDataQuality(null);
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
  }, [user, token, buildAnalyticsQuery, computePreviousRange, filters]);

  /**
   * CRITICAL: Reset ALL analytics state immediately.
   * 
   * Called after dataset deletion to ensure:
   * 1. No stale data is displayed
   * 2. UI shows empty states
   * 3. Next API call will fetch fresh (empty) data
   */
  const resetAllAnalytics = useCallback(() => {
    console.log('[DataContext] resetAllAnalytics called - clearing ALL state');
    
    // Immediately clear all state
    setSales([]);
    setForecast([]);
    setSegments([]);
    setRecommendations([]);
    setSentiment([]);
    setKpis(null);
    setInsights([]);
    setDataQuality(null);
    setCityOptions([]);
    setProductOptions([]);
    setLastTrainingDate(null);
    setError(null);
    
    // Clear local storage for this tenant (no stale cached data)
    if (user) {
      const tenantKey = `data_${user.company}`;
      localStorage.removeItem(tenantKey);
      console.log(`[DataContext] Cleared localStorage for ${tenantKey}`);
    }
  }, [user]);

  // Fetch data when user changes - DO NOT use localStorage for analytics
  useEffect(() => {
    fetchData();
  }, [user, fetchData]);

  /**
   * Handle local data upload simulation.
   * After upload, trigger a refresh to get fresh data from server.
   */
  const uploadData = useCallback(async (type: string, data: any[]) => {
    setIsProcessing(true);
    
    // Wait for backend pipeline to process
    // The actual upload is handled by DataUpload.tsx calling the API directly
    setTimeout(async () => {
      setIsProcessing(false);
      setLastTrainingDate(new Date().toISOString());
      
      // Refresh data from server to get fresh pipeline results
      console.log('[DataContext] uploadData complete - refreshing from server');
      await fetchData();
    }, 2000);
  }, [fetchData]);

  return (
    <DataContext.Provider value={{
      sales, forecast, segments, recommendations, sentiment, 
      kpis,
      insights,
      dataQuality,
      filters,
      setFilters,
      clearFilters,
      cityOptions,
      productOptions,
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
