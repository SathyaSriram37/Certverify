import { apiClient } from './client';
import { AdminCertificateItem, AdminStats, AdminUserItem, PaginatedResponse, User } from '../types';

export const getAdminStatsApi = async (): Promise<AdminStats> => {
  const response = await apiClient.get<AdminStats>('/api/v1/admin/stats');
  return response.data;
};

export const getAdminUsersApi = async (
  page: number = 1,
  size: number = 10,
  search?: string,
  role?: string
): Promise<PaginatedResponse<AdminUserItem>> => {
  const params: Record<string, any> = { page, size };
  if (search) params.search = search;
  if (role) params.role = role;
  const response = await apiClient.get<PaginatedResponse<AdminUserItem>>('/api/v1/admin/users', { params });
  return response.data;
};

export const updateAdminUserApi = async (
  userId: string,
  data: { role?: string; is_active?: boolean }
): Promise<User> => {
  const response = await apiClient.put<User>(`/api/v1/admin/users/${userId}`, data);
  return response.data;
};

export const getAdminCertificatesApi = async (
  page: number = 1,
  size: number = 10,
  verdict?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<PaginatedResponse<AdminCertificateItem>> => {
  const params: Record<string, any> = { page, size };
  if (verdict) params.verdict = verdict;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  const response = await apiClient.get<PaginatedResponse<AdminCertificateItem>>('/api/v1/admin/certificates', {
    params,
  });
  return response.data;
};

