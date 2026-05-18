
export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  COMPANY_ADMIN = 'company_admin',
  BRANCH_ADMIN = 'branch_admin',
  EMPLOYEE = 'employee',
  VIEWER = 'viewer',
  ADMIN = 'company_admin',
  BRANCH_MANAGER = 'branch_admin',
  ANALYST = 'viewer',
}

export const normalizeUserRole = (role?: string | UserRole | null): UserRole => {
  const value = String(role || '').trim().toLowerCase();

  switch (value) {
    case 'super_admin':
      return UserRole.SUPER_ADMIN;
    case 'admin':
    case 'company_admin':
      return UserRole.COMPANY_ADMIN;
    case 'branch_manager':
    case 'branch_admin':
      return UserRole.BRANCH_ADMIN;
    case 'employee':
      return UserRole.EMPLOYEE;
    case 'analyst':
    case 'viewer':
      return UserRole.VIEWER;
    default:
      return UserRole.VIEWER;
  }
};

export const isCompanyAdminRole = (role?: string | UserRole | null): boolean => {
  const normalized = normalizeUserRole(role);
  return normalized === UserRole.SUPER_ADMIN || normalized === UserRole.COMPANY_ADMIN;
};

export const isBranchAdminRole = (role?: string | UserRole | null): boolean => {
  return normalizeUserRole(role) === UserRole.BRANCH_ADMIN;
};

export const isReadOnlyRole = (role?: string | UserRole | null): boolean => {
  const normalized = normalizeUserRole(role);
  return normalized === UserRole.EMPLOYEE || normalized === UserRole.VIEWER;
};

export type AppPage =
  | 'dashboard'
  | 'sales'
  | 'forecasting'
  | 'segmentation'
  | 'recommendations'
  | 'sentiment'
  | 'inventory'
  | 'upload'
  | 'settings';

export const canSwitchBranches = (role?: string | UserRole | null): boolean => {
  return isCompanyAdminRole(role);
};

export const canManageBranchData = (role?: string | UserRole | null): boolean => {
  const normalized = normalizeUserRole(role);
  return normalized === UserRole.SUPER_ADMIN || normalized === UserRole.COMPANY_ADMIN || normalized === UserRole.BRANCH_ADMIN;
};

export const canAccessPage = (page: AppPage, role?: string | UserRole | null): boolean => {
  switch (page) {
    case 'settings':
      return isCompanyAdminRole(role);
    case 'upload':
      return canManageBranchData(role);
    default:
      return true;
  }
};

export interface User {
  id: string;
  email: string;
  name?: string;
  company: string;
  companyId?: number;
  branchId?: string | number | null;
  role: UserRole;
  avatar?: string;
}

export interface BranchManager {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
}

export interface Branch {
  id: number;
  name: string;
  city: string;
  phone?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
  manager?: BranchManager | null;
  created_at: string;
  status: string;
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
  branch_id?: string | null;
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

export interface MappingFieldDefinition {
  key: string;
  label: string;
  required: boolean;
  description: string;
  canonical_column: string;
}

export interface DatasetUploadPreparation {
  upload_id: string;
  dataset_type: 'sales' | 'customers' | 'reviews';
  file_name: string;
  row_count: number;
  columns: string[];
  preview_rows: Record<string, any>[];
  fields: MappingFieldDefinition[];
  suggested_mapping: Record<string, string | null>;
  saved_mapping: Record<string, string | null>;
  initial_mapping: Record<string, string | null>;
  mapping_source?: string | null;
  profile_id?: number | null;
  replace_dataset_id?: number | null;
  expires_at: string;
}

export interface DatasetMappingValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  mapping: Record<string, string | null>;
}

export interface DatasetMappingConfirmResponse {
  dataset: DatasetMeta;
  mapping_saved: boolean;
  standardized_columns: string[];
}

export interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  theme: 'light' | 'dark';
}
