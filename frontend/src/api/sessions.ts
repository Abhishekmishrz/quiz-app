import { apiRequest } from './client';
import type { SessionResponse } from '../types';

export function createSession(userId: string): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/sessions', {
    method: 'POST',
    body: { user_id: userId },
  });
}
