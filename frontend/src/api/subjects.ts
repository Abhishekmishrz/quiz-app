import { apiRequest } from './client';
import type { Subject } from '../types';

export function getSubjectsForExam(examId: string, userId: string): Promise<Subject[]> {
  return apiRequest<Subject[]>(`/exams/${examId}/subjects`, { userId });
}
