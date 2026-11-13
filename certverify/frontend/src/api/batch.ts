import { apiClient } from './client';

export interface BatchCertificateItem {
  certificate_id: string;
  filename: string;
  job_id?: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress_percentage: number;
  risk_score?: number | null;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | null;
  final_verdict?: 'VERIFIED' | 'SUSPICIOUS' | 'UNABLE_TO_VERIFY' | null;
  candidate_name?: string | null;
  organization_name?: string | null;
  created_at: string;
}

export interface BatchDetailResponse {
  batch_id: string;
  batch_name: string;
  total_count: number;
  completed_count: number;
  processing_count: number;
  failed_count: number;
  average_risk_score?: number | null;
  status: string;
  created_at: string;
  certificates: BatchCertificateItem[];
}

export interface BatchSummaryItem {
  batch_id: string;
  batch_name: string;
  total_count: number;
  completed_count: number;
  status: string;
  created_at: string;
}

export interface BatchUploadResponse {
  batch_id: string;
  batch_name: string;
  total_count: number;
  message: string;
  certificates: BatchCertificateItem[];
}

export const uploadBatchApi = async (formData: FormData): Promise<BatchUploadResponse> => {
  const res = await apiClient.post<BatchUploadResponse>('/api/v1/batch/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const getBatchDetailsApi = async (batchId: string): Promise<BatchDetailResponse> => {
  const res = await apiClient.get<BatchDetailResponse>(`/api/v1/batch/${batchId}`);
  return res.data;
};

export const listBatchesApi = async (): Promise<BatchSummaryItem[]> => {
  const res = await apiClient.get<BatchSummaryItem[]>('/api/v1/batch/');
  return res.data;
};

export const exportBatchCsvApi = async (batchId: string): Promise<Blob> => {
  const res = await apiClient.get(`/api/v1/batch/${batchId}/export`, {
    responseType: 'blob',
  });
  return res.data;
};

