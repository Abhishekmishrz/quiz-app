import { apiRequest } from './client';
import type { Exam } from '../types';

export function getExams(userId: string): Promise<Exam[]> {
  return apiRequest<Exam[]>('/exams', { userId });
}
