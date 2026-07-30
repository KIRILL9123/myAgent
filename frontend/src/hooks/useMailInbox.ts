import { useCallback, useEffect, useState } from 'react';
import { fetchUnreadEmails, searchEmails } from '../api/mail';
import type { EmailMessage, MailAccount } from '../types';

export function useMailInbox(account: MailAccount) {
  const [emails, setEmails] = useState<EmailMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const loadEmails = useCallback(async (searchStr?: string) => {
    setLoading(true);
    setError(null);
    try {
      const trimmedSearch = searchStr?.trim();
      const data = trimmedSearch
        ? await searchEmails(trimmedSearch, account)
        : await fetchUnreadEmails(account);
      setIsSearching(Boolean(trimmedSearch));
      setEmails(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка при загрузке почты');
    } finally {
      setLoading(false);
    }
  }, [account]);

  useEffect(() => {
    void loadEmails();
  }, [loadEmails]);

  return { emails, loading, error, isSearching, loadEmails, reload: loadEmails };
}
