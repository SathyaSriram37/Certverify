export type UserRole = 'USER' | 'ADMIN' | 'HR_VERIFIER';

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type ModuleStatus = 'PASS' | 'FAIL' | 'WARNING' | 'SKIPPED' | 'ERROR';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type FinalVerdict = 'VERIFIED' | 'SUSPICIOUS' | 'UNABLE_TO_VERIFY';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Certificate {
  id: string;
  original_filename: string;
  file_url: string;
  file_type: string;
  file_size_bytes: number;
  created_at: string;
  job_id?: string | null;
  job_status?: JobStatus | null;
  risk_score?: number | null;
  final_verdict?: FinalVerdict | null;
}

export interface VerificationJob {
  id: string;
  certificate_id: string;
  status: JobStatus;
  progress_percentage: number;
  current_step: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface VerificationResult {
  id: string;
  job_id?: string;
  module_name: string;
  status: ModuleStatus;
  finding_summary: string;
  details: Record<string, any>;
  confidence_score: number | null;
  created_at: string;
}

export interface RiskAssessment {
  id: string;
  job_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  final_verdict: FinalVerdict;
  reasoning: string;
  report_url: string | null;
  created_at: string;
}

export interface ResultsResponse {
  job: VerificationJob;
  results: VerificationResult[];
  risk_assessment: RiskAssessment | null;
  certificate: Certificate | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface UploadResponse {
  certificate_id: string;
  job_id: string;
  filename: string;
  status: JobStatus;
}

export interface DailyUploadStat {
  date: string;
  count: number;
}

export interface RecentUploadItem {
  certificate_id: string;
  job_id?: string | null;
  filename: string;
  file_type: string;
  status: JobStatus;
  risk_score?: number | null;
  final_verdict?: FinalVerdict | null;
  created_at: string;
}

export interface DashboardStats {
  total_uploads: number;
  verified_count: number;
  suspicious_count: number;
  unable_count: number;
  processing_count: number;
  avg_risk_score: number;
  uploads_by_day: DailyUploadStat[];
  recent_uploads: RecentUploadItem[];
}

export interface AdminStats {
  total_users: number;
  total_certificates: number;
  verdicts: Record<string, number>;
  suspicious_this_week: number;
  avg_processing_seconds: number;
  daily_uploads_30d: DailyUploadStat[];
}

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  upload_count: number;
}

export interface AdminCertificateItem {
  id: string;
  user_id: string;
  user_email: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  created_at: string;
  job_id?: string | null;
  status?: JobStatus | null;
  risk_score?: number | null;
  final_verdict?: FinalVerdict | null;
  is_suspicious: boolean;
}

