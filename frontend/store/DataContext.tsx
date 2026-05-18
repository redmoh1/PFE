
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
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
  canSwitchBranches,
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
  isProcessing: boolean;
  isLoading: boolean;
  error: string | null;
  uploadData: (type: string, data: any[]) => void;
  refreshData: () => Promise<void>;
  resetAllAnalytics: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, selectedBranchId } = useAuth();
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
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const clearAnalyticsState = useCallback(() => {
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
  }, []);

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
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    activeControllerRef.current?.abort();

    if (!user) {
      clearAnalyticsState();
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    activeControllerRef.current = controller;
    const isCurrentRequest = () => requestIdRef.current === requestId && !controller.signal.aborted;
    const applyIfCurrent = (updater: () => void) => {
      if (isCurrentRequest()) {
        updater();
      }
    };

    setIsLoading(true);
    setError(null);

    const branchFromUser = user?.branchId !== undefined && user?.branchId !== null ? String(user.branchId) : '';
    const effectiveBranch = canSwitchBranches(user?.role)
      ? selectedBranchId || ''
      : branchFromUser || selectedBranchId || '';
    const fetchOpts: RequestInit = { cache: 'no-store', signal: controller.signal };

    const getJson = async (url: string) => {
      const response = await authFetch(url, fetchOpts);
      if (!isCurrentRequest()) {
        return { ok: false, empty: false, stale: true, data: null };
      }
      if (response.status === 204) return { ok: true, empty: true, data: null };
      if (!response.ok) return { ok: false, empty: false, data: null };
      const payload = await response.json();
      if (!isCurrentRequest()) {
        return { ok: false, empty: false, stale: true, data: null };
      }
      return { ok: true, empty: false, stale: false, data: payload?.data || payload };
    };

    const analyticsParams = buildAnalyticsQuery();
    if (effectiveBranch) {
      analyticsParams.set('branch_id', effectiveBranch);
    }
    const analyticsQs = analyticsParams.toString();
    const analyticsSuffix = analyticsQs ? `?${analyticsQs}` : '';

    const dateOnlyParams = buildAnalyticsQuery({}, { includeCityProduct: false });
    if (effectiveBranch) {
      dateOnlyParams.set('branch_id', effectiveBranch);
    }
    const dateOnlyQs = dateOnlyParams.toString();
    const dateOnlySuffix = dateOnlyQs ? `?${dateOnlyQs}` : '';

    try {
      // Fetch KPIs
      try {
        const kpiRes = await getJson(`/api/kpis${analyticsSuffix}`);
        if (kpiRes.stale) return;
        if (kpiRes.empty) {
          applyIfCurrent(() => setKpis(null));
        } else if (kpiRes.ok) {
          applyIfCurrent(() => setKpis(kpiRes.data));
        } else {
          applyIfCurrent(() => setKpis(null));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch KPIs:', e);
        applyIfCurrent(() => setKpis(null));
      }

      // Fetch filter options (date-scoped, not city/product scoped)
      try {
        const citiesRes = await getJson(`/api/top-cities${dateOnlySuffix ? `${dateOnlySuffix}&limit=50` : '?limit=50'}`);
        if (citiesRes.stale) return;
        if (citiesRes.ok && !citiesRes.empty) {
          const data = citiesRes.data;
          const options = (Array.isArray(data) ? data : []).map((c: any) => String(c.city)).filter(Boolean);
          applyIfCurrent(() => setCityOptions(options));
        } else {
          applyIfCurrent(() => setCityOptions([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch city options:', e);
        applyIfCurrent(() => setCityOptions([]));
      }

      try {
        const productsRes = await getJson(`/api/top-products${dateOnlySuffix ? `${dateOnlySuffix}&limit=50` : '?limit=50'}`);
        if (productsRes.stale) return;
        if (productsRes.ok && !productsRes.empty) {
          const data = productsRes.data;
          const options = (Array.isArray(data) ? data : []).map((p: any) => String(p.product_id)).filter(Boolean);
          applyIfCurrent(() => setProductOptions(options));
        } else {
          applyIfCurrent(() => setProductOptions([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch product options:', e);
        applyIfCurrent(() => setProductOptions([]));
      }

      // Fetch sales data (raw data endpoint)
      try {
        const salesParams = buildAnalyticsQuery();
        salesParams.set('limit', '100');
        if (effectiveBranch) salesParams.set('branch_id', effectiveBranch);
        const salesRes = await getJson(`/api/raw-data?${salesParams.toString()}`);
        if (salesRes.stale) return;
        if (salesRes.empty) {
          applyIfCurrent(() => setSales([]));
        } else if (salesRes.ok) {
          const salesData = salesRes.data;
          applyIfCurrent(() => setSales(salesData.map((item: any, idx: number) => ({
            id: item.OrderID || item.Product_ID || `s-${idx}`,
            date: item.OrderDate || item.Sale_Date || item.Date || new Date().toISOString().split('T')[0],
            amount: item.TotalPrice || item.Sales_Amount || 0,
            product: item.ProductID || item.Product_ID || 'Unknown',
            category: 'Product',
            city: item.City || item.Region || 'Unknown',
            customerId: item.CustomerID || 'c-unknown'
          }))));
        } else {
          applyIfCurrent(() => setSales([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch sales data:', e);
        applyIfCurrent(() => setSales([]));
      }

      // Fetch forecast data
      try {
        const forecastRes = await getJson(`/api/monthly-sales${analyticsSuffix}`);
        if (forecastRes.stale) return;
        if (forecastRes.empty) {
          applyIfCurrent(() => setForecast([]));
        } else if (forecastRes.ok) {
          const forecastData = forecastRes.data;
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
              if (effectiveBranch) {
                prevParams.set('branch_id', effectiveBranch);
              }
              const prevRes = await getJson(`/api/monthly-sales?${prevParams.toString()}`);
              if (prevRes.stale) return;
              if (prevRes.ok && !prevRes.empty) {
                const prevData = prevRes.data;
                const prevPoints: ForecastPoint[] = (Array.isArray(prevData) ? prevData : []).map((item: any) => ({
                  date: item.month || item.date,
                  actual: item.actual_sales ?? item.actual ?? undefined,
                  forecast: item.forecasted_sales ?? item.forecast ?? undefined,
                }));
                const merged = currentPoints.map((p, index) => {
                  const prevPoint = prevPoints[index];
                  return {
                    ...p,
                    previous_actual: prevPoint?.actual,
                    previous_forecast: prevPoint?.forecast,
                    previous_period_date: prevPoint?.date,
                  };
                });
                applyIfCurrent(() => setForecast(merged));
              } else {
                applyIfCurrent(() => setForecast(currentPoints));
              }
            } else {
              applyIfCurrent(() => setForecast(currentPoints));
            }
          } else {
            applyIfCurrent(() => setForecast(currentPoints));
          }
        } else {
          applyIfCurrent(() => setForecast([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch forecast data:', e);
        applyIfCurrent(() => setForecast([]));
      }

      // Fetch recommendations - ALWAYS fresh from server with JWT auth
      try {
        const recsRes = await getJson('/api/recommendations?limit=10');
        if (recsRes.stale) return;
        if (recsRes.empty) {
          console.log('[DataContext] Recommendations API returned 204 - clearing state');
          applyIfCurrent(() => setRecommendations([]));
        } else if (recsRes.ok) {
          const recsData = recsRes.data;
          if (Array.isArray(recsData) && recsData.length > 0) {
            applyIfCurrent(() => setRecommendations(recsData.map((item: any, idx: number) => ({
              id: `rec-${idx}`,
              baseProduct: item.if_product || '',
              recommendedProduct: item.then_product || '',
              confidence: item.confidence || 0,
              lift: item.lift || 0
            }))));
          } else {
            applyIfCurrent(() => setRecommendations([]));
          }
        } else {
          console.warn('Recommendations API returned non-OK status:', recsRes.status);
          applyIfCurrent(() => setRecommendations([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch recommendations:', e);
        applyIfCurrent(() => setRecommendations([]));
      }

      // Fetch RFM segmentation data - ALWAYS fresh from server with JWT auth
      try {
        const segmentRes = await getJson('/api/segmentation');
        if (segmentRes.stale) return;
        if (segmentRes.empty) {
          console.log('[DataContext] Segmentation API returned 204 - clearing state');
          applyIfCurrent(() => setSegments([]));
        } else if (segmentRes.ok) {
          const segmentData = segmentRes.data;
          const segmentsArr = segmentData.segments || segmentData;
          if (Array.isArray(segmentsArr) && segmentsArr.length > 0) {
            applyIfCurrent(() => setSegments(segmentsArr.map((item: any) => ({
              name: item.segment || item.name,
              count: item.customer_count || item.count,
              color: item.color,
              recency: item.avg_recency || item.recency,
              frequency: item.avg_frequency || item.frequency,
              monetary: item.avg_monetary || item.monetary
            }))));
          } else {
            applyIfCurrent(() => setSegments([]));
          }
        } else {
          console.warn('Segmentation API returned non-OK status:', segmentRes.status);
          applyIfCurrent(() => setSegments([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch segmentation:', e);
        applyIfCurrent(() => setSegments([]));
      }

      // Fetch Decision Insights (rule-based)
      try {
        const insightsParams = buildAnalyticsQuery();
        insightsParams.set('limit', '8');
        if (effectiveBranch) insightsParams.set('branch_id', effectiveBranch);
        const insightsRes = await getJson(`/api/insights?${insightsParams.toString()}`);
        if (insightsRes.stale) return;
        if (insightsRes.empty) {
          applyIfCurrent(() => setInsights([]));
        } else if (insightsRes.ok) {
          const payload = insightsRes.data;
          const items = payload?.insights || payload || [];
          applyIfCurrent(() => setInsights(Array.isArray(items) ? items : []));
        } else {
          applyIfCurrent(() => setInsights([]));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch insights:', e);
        applyIfCurrent(() => setInsights([]));
      }

      // Fetch Data Quality Report
      try {
        const dqRes = await getJson('/api/data-quality');
        if (dqRes.stale) return;
        if (dqRes.empty) {
          applyIfCurrent(() => setDataQuality(null));
        } else if (dqRes.ok) {
          applyIfCurrent(() => setDataQuality(dqRes.data));
        } else {
          applyIfCurrent(() => setDataQuality(null));
        }
      } catch (e) {
        if (!isCurrentRequest()) return;
        console.error('Failed to fetch data quality report:', e);
        applyIfCurrent(() => setDataQuality(null));
      }

      applyIfCurrent(() => setError(null));
    } catch (err) {
      if (!isCurrentRequest()) return;
      if (controller.signal.aborted) return;
      console.error('Failed to fetch data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      applyIfCurrent(() => setError(`Failed to load data from server: ${errorMessage}`));
    } finally {
      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
      if (isCurrentRequest()) {
        setIsLoading(false);
      }
    }
  }, [user, selectedBranchId, authFetch, buildAnalyticsQuery, computePreviousRange, filters, clearAnalyticsState]);

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
    requestIdRef.current += 1;
    activeControllerRef.current?.abort();
    activeControllerRef.current = null;
    
    // Immediately clear all state
    clearAnalyticsState();
    setError(null);
    
    // Clear local storage for this tenant (no stale cached data)
    if (user) {
      const tenantKey = `data_${user.company}`;
      localStorage.removeItem(tenantKey);
      console.log(`[DataContext] Cleared localStorage for ${tenantKey}`);
    }
  }, [user, clearAnalyticsState]);

  useEffect(() => {
    return () => {
      activeControllerRef.current?.abort();
    };
  }, []);

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
      isProcessing, isLoading, error,
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
