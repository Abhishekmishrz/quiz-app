import { apiRequest } from './client';
import type { Chapter } from '../types';

export function getChaptersForSubject(subjectId: string, userId: string): Promise<Chapter[]> {
  return apiRequest<Chapter[]>(`/subjects/${subjectId}/chapters`, { userId });
}
