import { apiRequest } from './client';
import type { User } from '../types';

interface PagedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export async function getUsers(): Promise<User[]> {
  const page = await apiRequest<PagedResponse<User>>('/users', { query: { limit: 200 } });
  return page.items;
}
