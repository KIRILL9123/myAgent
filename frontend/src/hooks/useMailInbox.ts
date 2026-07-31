import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUnreadEmails, searchEmails } from '../api/mail';
import type { EmailMessage, MailAccount } from '../types';

export function useMailInbox(account: MailAccount) {
  const [search, setSearch] = useState('');
  useEffect(() => { setSearch(''); }, [account]);

  const query = useQuery({ queryKey: ['mail', account, search], queryFn: () => search ? searchEmails(search, account) : fetchUnreadEmails(account), staleTime: 30_000 });
  const loadEmails = (value = '') => setSearch(value.trim());

  return { emails: query.data ?? ([] as EmailMessage[]), loading: query.isLoading, error: query.error instanceof Error ? query.error.message : null, isSearching: Boolean(search), loadEmails, reload: query.refetch };
}
