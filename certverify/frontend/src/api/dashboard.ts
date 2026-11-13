import { apiClient } from './client';
import { DashboardStats } from '../types';

export const getDashboardStatsApi = async (): Promise<DashboardStats> => {
  const response = await apiClient.get<DashboardStats>('/api/v1/dashboard/stats');
  return response.data;
};

