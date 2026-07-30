import { useCallback, useEffect, useState } from 'react';
import {
  fetchRecurringTemplates,
  fetchSummary,
  fetchTransactions,
} from '../api/finance';
import type {
  FinanceRange,
  FinanceSummary,
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
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [recurringTemplates, setRecurringTemplates] = useState<RecurringTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { startDate, endDate } = getRangeDates(range);
      const [nextTransactions, nextSummary, nextTemplates] = await Promise.all([
        fetchTransactions(startDate, endDate),
        fetchSummary(startDate, endDate),
        fetchRecurringTemplates(),
      ]);
      setTransactions(nextTransactions);
      setSummary(nextSummary);
      setRecurringTemplates(nextTemplates);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки финансовых данных');
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { transactions, summary, recurringTemplates, loading, error, reload };
}
