import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  fetchRecurringTemplates,
  fetchSummary,
  fetchTransactions,
} from '../api/finance';
import type {
  FinanceRange,
  RecurringTemplate,
  Transaction,
} from '../types';

function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getRangeDates(range: FinanceRange): { startDate: string; endDate: string } {
  const now = new Date();

  if (range === 'today') {
    const date = formatLocalDate(now);
    return { startDate: date, endDate: date };
  }

  if (range === 'week') {
    const distanceToMonday = now.getDay() === 0 ? 6 : now.getDay() - 1;
    const monday = new Date(now);
    monday.setDate(now.getDate() - distanceToMonday);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return { startDate: formatLocalDate(monday), endDate: formatLocalDate(sunday) };
  }

  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { startDate: formatLocalDate(firstDay), endDate: formatLocalDate(lastDay) };
}

export function useFinanceData(range: FinanceRange) {
  const dates = useMemo(() => getRangeDates(range), [range]);
  const query = useQuery({ queryKey: ['finance', range, dates.startDate, dates.endDate], queryFn: async () => {
      const [transactions, summary, recurringTemplates] = await Promise.all([
        fetchTransactions(dates.startDate, dates.endDate),
        fetchSummary(dates.startDate, dates.endDate),
        fetchRecurringTemplates(),
      ]);
      return { transactions, summary, recurringTemplates };
  }, staleTime: 30_000 });

  return { transactions: query.data?.transactions ?? ([] as Transaction[]), summary: query.data?.summary ?? null, recurringTemplates: query.data?.recurringTemplates ?? ([] as RecurringTemplate[]), loading: query.isLoading, error: query.error instanceof Error ? query.error.message : null, reload: () => query.refetch() };
}
