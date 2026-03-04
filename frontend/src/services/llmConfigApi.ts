// LLM Configuration API service
import axios from 'axios';
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
    const response = await axios.get(`${API_BASE}/llm-configs`);
    return response.data;
  },

  // Create new LLM configuration
  createConfig: async (data: LLMConfigCreate): Promise<LLMConfig> => {
    const response = await axios.post(`${API_BASE}/llm-configs`, data);
    return response.data;
  },

  // Update LLM configuration
  updateConfig: async (id: string, data: LLMConfigUpdate): Promise<LLMConfig> => {
    const response = await axios.put(`${API_BASE}/llm-configs/${id}`, data);
    return response.data;
  },

  // Delete LLM configuration
  deleteConfig: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/llm-configs/${id}`);
  },

  // Test LLM connection
  testConnection: async (id: string): Promise<TestConnectionResult> => {
    const response = await axios.post(`${API_BASE}/llm-configs/${id}/test`);
    return response.data;
  },
};

// Application endpoints
export const applicationApi = {
  // Fetch all applications
  fetchApplications: async (): Promise<Application[]> => {
    const response = await axios.get(`${API_BASE}/llm-configs/applications`);
    return response.data;
  },

  // Fetch single application by code
  fetchApplicationByCode: async (code: string): Promise<Application> => {
    const response = await axios.get(`${API_BASE}/llm-configs/applications/${code}`);
    return response.data;
  },
};

// LLM Binding endpoints
export const bindingApi = {
  // Fetch bindings with optional filters
  fetchBindings: async (applicationId?: string): Promise<LLMBinding[]> => {
    const params = applicationId ? { application_id: applicationId } : {};
    const response = await axios.get(`${API_BASE}/llm-configs/bindings`, { params });
    return response.data;
  },

  // Create new binding
  createBinding: async (data: LLMBindingCreate): Promise<LLMBinding> => {
    const response = await axios.post(`${API_BASE}/llm-configs/bindings`, data);
    return response.data;
  },

  // Update binding
  updateBinding: async (id: string, data: LLMBindingUpdate): Promise<LLMBinding> => {
    const response = await axios.put(`${API_BASE}/llm-configs/bindings/${id}`, data);
    return response.data;
  },

  // Delete binding
  deleteBinding: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/llm-configs/bindings/${id}`);
  },
};
