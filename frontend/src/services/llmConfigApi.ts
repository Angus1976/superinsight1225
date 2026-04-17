// LLM Configuration API service
import apiClient from './api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  LLMConfig,
  LLMConfigCreate,
  LLMConfigUpdate,
  Application,
  LLMBinding,
  LLMBindingCreate,
  LLMBindingUpdate,
  TestConnectionResult,
} from '@/types/llmConfig';

const API_BASE = '/api';

// LLM Configuration endpoints
export const llmConfigApi = {
  // Fetch all LLM configurations
  fetchConfigs: async (): Promise<LLMConfig[]> => {
    const response = await apiClient.get(`${API_BASE}/llm-configs`);
    return apiResponseToSnake<LLMConfig[]>(response.data);
  },

  // Create new LLM configuration
  createConfig: async (data: LLMConfigCreate): Promise<LLMConfig> => {
    const response = await apiClient.post(`${API_BASE}/llm-configs`, apiRequestToSnake(data));
    return apiResponseToSnake<LLMConfig>(response.data);
  },

  // Update LLM configuration
  updateConfig: async (id: string, data: LLMConfigUpdate): Promise<LLMConfig> => {
    const response = await apiClient.put(`${API_BASE}/llm-configs/${id}`, apiRequestToSnake(data));
    return apiResponseToSnake<LLMConfig>(response.data);
  },

  // Delete LLM configuration
  deleteConfig: async (id: string): Promise<void> => {
    await apiClient.delete(`${API_BASE}/llm-configs/${id}`);
  },

  // Test LLM connection
  testConnection: async (id: string): Promise<TestConnectionResult> => {
    const response = await apiClient.post(`${API_BASE}/llm-configs/${id}/test`);
    return apiResponseToSnake<TestConnectionResult>(response.data);
  },
};

// Application endpoints
export const applicationApi = {
  // Fetch all applications
  fetchApplications: async (): Promise<Application[]> => {
    const response = await apiClient.get(`${API_BASE}/llm-configs/applications`);
    return apiResponseToSnake<Application[]>(response.data);
  },

  // Fetch single application by code
  fetchApplicationByCode: async (code: string): Promise<Application> => {
    const response = await apiClient.get(`${API_BASE}/llm-configs/applications/${code}`);
    return apiResponseToSnake<Application>(response.data);
  },
};

// LLM Binding endpoints
export const bindingApi = {
  // Fetch bindings with optional filters
  fetchBindings: async (applicationId?: string): Promise<LLMBinding[]> => {
    const params = applicationId ? { application_id: applicationId } : {};
    const response = await apiClient.get(`${API_BASE}/llm-configs/bindings`, { params });
    return apiResponseToSnake<LLMBinding[]>(response.data);
  },

  // Create new binding
  createBinding: async (data: LLMBindingCreate): Promise<LLMBinding> => {
    const response = await apiClient.post(`${API_BASE}/llm-configs/bindings`, apiRequestToSnake(data));
    return apiResponseToSnake<LLMBinding>(response.data);
  },

  // Update binding
  updateBinding: async (id: string, data: LLMBindingUpdate): Promise<LLMBinding> => {
    const response = await apiClient.put(
      `${API_BASE}/llm-configs/bindings/${id}`,
      apiRequestToSnake(data)
    );
    return apiResponseToSnake<LLMBinding>(response.data);
  },

  // Delete binding
  deleteBinding: async (id: string): Promise<void> => {
    await apiClient.delete(`${API_BASE}/llm-configs/bindings/${id}`);
  },
};
