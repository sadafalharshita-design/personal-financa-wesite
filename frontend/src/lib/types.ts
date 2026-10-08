export interface User {
  id: string;
  email: string;
  name: string;
  image_url: string | null;
  onboarded: boolean;
}

export interface AuthResponse { user: User }

export interface Account {
  id: string;
  name: string;
  type: "CURRENT" | "SAVINGS";
  balance: number;
  is_default: boolean;
  created_at: string;
}

export interface TransactionInput {
  type: "INCOME" | "EXPENSE";
  amount: number;
  description: string;
  date: string;
  category: string;
  merchant: string | null;
  account_id: string;
  is_recurring: boolean;
  recurring_interval: "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY" | null;
}

export interface Transaction extends TransactionInput {
  id: string;
  status: "COMPLETED";
  created_at: string;
}

export interface TransactionList { items: Transaction[]; total: number }

export interface Budget {
  monthly_limit: number;
  spent: number;
  remaining: number;
  usage_percentage: number;
  alert_threshold: number;
  month: string;
}

export interface Goal {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  priority: number;
  category: string;
  remaining_amount: number;
  progress_percentage: number;
  projected_completion: string | null;
  created_at: string;
}

export interface CategorySpend { category: string; amount: number }
export interface MonthlyFlow { month: string; income: number; expenses: number }

export interface DashboardSummary {
  total_balance: number;
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  budget_remaining: number;
  savings_rate: number;
  largest_category: string | null;
  category_spend: CategorySpend[];
  monthly_flow: MonthlyFlow[];
  recent_transactions: Transaction[];
  goals: Goal[];
}

export interface ProjectionPoint { month: number; baseline: number; simulated: number }

export interface ScenarioResult {
  id: string;
  query: string;
  scenario_type: string;
  scenario_summary: string;
  baseline_monthly_income: number;
  baseline_monthly_expenses: number;
  baseline_monthly_savings: number;
  simulated_monthly_expenses: number;
  simulated_monthly_savings: number;
  current_balance: number;
  projections: ProjectionPoint[];
  goal_name: string | null;
  baseline_goal_months: number | null;
  simulated_goal_months: number | null;
  goal_acceleration_months: number;
  affordability_months: number | null;
  ai_explanation: string;
  ai_powered: boolean;
  assumptions: string[];
  created_at: string;
}

export interface ReceiptExtraction {
  merchant: string | null;
  amount: number;
  date: string | null;
  category: string;
  description: string;
  type: "INCOME" | "EXPENSE";
}

export interface ReceiptScanResponse {
  extraction: ReceiptExtraction;
  warnings: string[];
  ai_powered: boolean;
}