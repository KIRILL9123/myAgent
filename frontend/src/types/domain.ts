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
  category: string;
  description: string;
  date: string;
}

export interface FinanceSummary {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expense: number;
  net_balance: number;
  expense_breakdown: { category: string; amount: number }[];
  income_breakdown: { category: string; amount: number }[];
}

export interface TransactionCreateInput {
  type: 'income' | 'expense';
  amount: number;
  category: string;
  description?: string;
  date?: string;
  is_recurring?: boolean;
}

export interface RecurringTemplate {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  category: string;
  description: string;
  day_of_month: number;
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
