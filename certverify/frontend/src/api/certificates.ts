import { apiClient } from './client';
import { Certificate, PaginatedResponse, ResultsResponse, UploadResponse, VerificationJob } from '../types';

export const uploadCertificateApi = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<UploadResponse>('/api/v1/certificates/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getCertificatesApi = async (
  page: number = 1,
  size: number = 10,
  status?: string
): Promise<PaginatedResponse<Certificate>> => {
  const params: Record<string, any> = { page, size };
  if (status) params.status = status;
  const response = await apiClient.get<PaginatedResponse<Certificate>>('/api/v1/certificates/', { params });
  return response.data;
};

export const deleteCertificateApi = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/certificates/${id}`);
};

export const getJobStatusApi = async (jobId: string): Promise<VerificationJob> => {
  const response = await apiClient.get<VerificationJob>(`/api/v1/verify/${jobId}/status`);
  return response.data;
};

export const getResultsApi = async (jobId: string): Promise<ResultsResponse> => {
  const response = await apiClient.get<ResultsResponse>(`/api/v1/verify/${jobId}/results`);
  return response.data;
};

export const getReportUrlApi = async (jobId: string): Promise<{ report_url: string }> => {
  const response = await apiClient.get<{ report_url: string }>(`/api/v1/verify/${jobId}/report`);
  return response.data;
};

