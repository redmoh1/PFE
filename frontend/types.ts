
export enum UserRole {
  ADMIN = 'admin',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
}

export interface User {
  id: string;
  email: string;
  name?: string;
  company: string;
  companyId?: number;
  role: UserRole;
  avatar?: string;
}

export interface SalesData {
  id: string;
  date: string;
  amount: number;
  product: string;
  category: string;
  city: string;
  customerId: string;
}

export interface ForecastPoint {
  date: string;
  actual?: number;
  forecast?: number;
  forecast_upper?: number;
  forecast_lower?: number;
  // Comparison mode (previous period)
  previous_actual?: number;
  previous_forecast?: number;
}

export interface AnalyticsFilters {
  startDate: string;
  endDate: string;
  city: string;
  product: string;
  comparePrevious: boolean;
}

export interface RFMSegment {
  name: string;
  count: number;
  color: string;
  recency?: number;
  frequency?: number;
  monetary?: number;
}

export interface Recommendation {
  id: string;
  baseProduct: string;
  recommendedProduct: string;
  confidence: number;
  lift: number;
}

export interface SentimentData {
  label: 'Positive' | 'Neutral' | 'Negative';
  score: number;
  count: number;
}

export interface KPIData {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  top_product: string;
  top_city: string;
  // Percentage changes (null = comparison unavailable)
  revenue_change: number | null;
  orders_change: number | null;
  aov_change: number | null;
}

export type InsightSeverity = 'info' | 'warning' | 'critical';

export interface DecisionInsight {
  id: string;
  severity: InsightSeverity;
  title: string;
  description: string;
  reason: string;
  suggested_action: string;
  metrics?: Record<string, any>;
}

export type DataQualityIssueLevel = 'info' | 'warning' | 'critical';

export interface DataQualityIssue {
  id: string;
  level: DataQualityIssueLevel;
  message: string;
  affected_columns: string[];
  metrics: Record<string, any>;
}

export interface DataQualityReport {
  company_id: string;
  dataset: string;
  generated_at: string;
  row_count: number;
  column_count: number;
  date_column?: string | null;
  date_min?: string | null;
  date_max?: string | null;
  missing_values: Record<string, { missing_count: number; missing_pct: number }>;
  invalid_values: Record<string, { invalid_count: number; invalid_pct: number; type: string }>;
  duplicates: { duplicate_rows: number; duplicate_pct: number };
  outliers: Record<string, Record<string, any>>;
  quality_score: number;
  issues: DataQualityIssue[];
}

export interface DatasetMeta {
  id: number;
  company_id: string;
  dataset_type: string;
  file_name: string;
  row_count: number;
  uploaded_at: string;
  is_active: boolean;
}

export interface DatasetPreview {
  id: number;
  file_name: string;
  dataset_type: string;
  uploaded_at: string;
  row_count: number;
  columns: string[];
  rows: Record<string, any>[];
}

export interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  theme: 'light' | 'dark';
}
