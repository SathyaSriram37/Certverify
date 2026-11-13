import { apiClient } from './client';
import { User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const loginApi = async (formData: FormData): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const registerApi = async (data: {
  email: string;
  password: string;
  full_name: string;
}): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/api/v1/auth/register', data);
  return response.data;
};

export const getMeApi = async (): Promise<User> => {
  const response = await apiClient.get<User>('/api/v1/auth/me');
  return response.data;
};

export const updateProfileApi = async (data: {
  full_name?: string;
  current_password?: string;
  new_password?: string;
}): Promise<User> => {
  const response = await apiClient.put<User>('/api/v1/auth/me', data);
  return response.data;
};

