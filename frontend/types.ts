
export enum UserRole {
  ADMIN = 'ADMIN',
  ANALYST = 'ANALYST',
}

export interface User {
  id: string;
  email: string;
  company: string;
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
