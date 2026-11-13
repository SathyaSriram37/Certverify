import { apiClient } from './client';

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  rate_limit_per_minute: number;
  is_active: boolean;
  last_used_at?: string | null;
  created_at: string;
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  raw_key: string;
  key_prefix: string;
  rate_limit_per_minute: number;
  created_at: string;
  message: string;
}

export interface WebhookConfig {
  id: string;
  url: string;
  secret: string;
  is_active: boolean;
  last_delivered_at?: string | null;
  created_at: string;
}

export interface WebhookTestResult {
  success: boolean;
  http_status?: number;
  message: string;
  delivered_at: string;
}

export const createApiKeyApi = async (name: string, rateLimit = 60): Promise<ApiKeyCreatedResponse> => {
  const res = await apiClient.post<ApiKeyCreatedResponse>('/api/v1/developer/keys', {
    name,
    rate_limit_per_minute: rateLimit,
  });
  return res.data;
};

export const listApiKeysApi = async (): Promise<ApiKeyItem[]> => {
  const res = await apiClient.get<ApiKeyItem[]>('/api/v1/developer/keys');
  return res.data;
};

export const revokeApiKeyApi = async (keyId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/developer/keys/${keyId}`);
};

export const getWebhookConfigApi = async (): Promise<WebhookConfig | null> => {
  const res = await apiClient.get<WebhookConfig | null>('/api/v1/developer/webhook');
  return res.data;
};

export const updateWebhookConfigApi = async (url: string, secret?: string): Promise<WebhookConfig> => {
  const res = await apiClient.post<WebhookConfig>('/api/v1/developer/webhook', {
    url,
    secret,
  });
  return res.data;
};

export const testWebhookApi = async (): Promise<WebhookTestResult> => {
  const res = await apiClient.post<WebhookTestResult>('/api/v1/developer/webhook/test');
  return res.data;
};

