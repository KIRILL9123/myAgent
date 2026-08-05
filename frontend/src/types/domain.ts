export type FinanceRange = 'today' | 'week' | 'month';

export type MailAccount = 'gmail' | 'ukrnet';

export interface MailFormState {
  to: string;
  subject: string;
  body: string;
}

export interface Transaction {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  currency: string;
  category: string;
  description: string;
  date: string;
  source_template_id?: number | null;
}

export interface FinanceSummary {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expense: number;
  net_balance: number;
  expense_breakdown: { category: string; amount: number }[];
  income_breakdown: { category: string; amount: number }[];
  currency: string;
  display_currency: string;
  currencies: string[];
  mixed_currency: boolean;
  by_currency: Record<string, { total_income: number; total_expense: number; net_balance: number }>;
}

export interface TransactionCreateInput {
  type: 'income' | 'expense';
  amount: number;
  currency?: string;
  category: string;
  description?: string;
  date?: string;
  is_recurring?: boolean;
  frequency?: 'weekly' | 'monthly' | 'yearly';
}

export interface TransactionUpdateInput {
  type?: 'income' | 'expense';
  amount?: number;
  category?: string;
  description?: string;
  date?: string;
}

export interface RecurringTemplate {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  currency: string;
  category: string;
  description: string;
  day_of_month: number | null;
  frequency: 'weekly' | 'monthly' | 'yearly';
  day_of_week: number | null;
  month_of_year: number | null;
  active: boolean;
}

export interface FinanceForecastOccurrence {
  template_id: number;
  date: string;
  type: 'income' | 'expense';
  amount: number;
  currency: string;
  category: string;
  description: string;
  frequency: 'weekly' | 'monthly' | 'yearly';
}

export interface FinanceForecastTotals {
  total_income: number;
  total_expense: number;
  net_balance: number;
  occurrences: number;
}

export interface FinanceForecast {
  start_date: string;
  end_date: string;
  months: number;
  currencies: string[];
  by_currency: Record<string, FinanceForecastTotals>;
  occurrences: FinanceForecastOccurrence[];
}

export interface EmailMessage {
  from: string;
  to: string;
  subject: string;
  date: string;
  preview: string;
}

export interface EmailSendInput {
  to: string;
  subject: string;
  body: string;
  account?: string;
}
