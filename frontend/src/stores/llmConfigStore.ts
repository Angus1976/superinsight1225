// LLM Configuration store
import { create } from 'zustand';
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
import { llmConfigApi, applicationApi, bindingApi } from '@/services/llmConfigApi';

interface LLMConfigState {
  // State
  configs: LLMConfig[];
  applications: Application[];
  bindings: LLMBinding[];
  loading: boolean;
  error: string | null;

  // LLM Config Actions
  fetchConfigs: () => Promise<void>;
  createConfig: (data: LLMConfigCreate) => Promise<void>;
  updateConfig: (id: string, data: LLMConfigUpdate) => Promise<void>;
  deleteConfig: (id: string) => Promise<void>;
  testConnection: (id: string) => Promise<TestConnectionResult>;

  // Application Actions
  fetchApplications: () => Promise<void>;

  // Binding Actions
  fetchBindings: (applicationId?: string) => Promise<void>;
  createBinding: (data: LLMBindingCreate) => Promise<void>;
  updateBinding: (id: string, data: LLMBindingUpdate) => Promise<void>;
  deleteBinding: (id: string) => Promise<void>;
  reorderBindings: (applicationId: string, newOrder: string[]) => Promise<void>;

  // Utility Actions
  clearError: () => void;
}

export const useLLMConfigStore = create<LLMConfigState>((set, get) => ({
  // Initial state
  configs: [],
  applications: [],
  bindings: [],
  loading: false,
  error: null,

  // Fetch all LLM configurations
  fetchConfigs: async () => {
    set({ loading: true, error: null });
    try {
      const configs = await llmConfigApi.fetchConfigs();
      set({ configs, loading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to fetch configurations',
        loading: false 
      });
    }
  },

  // Create new LLM configuration
  createConfig: async (data: LLMConfigCreate) => {
    set({ loading: true, error: null });
    try {
      const newConfig = await llmConfigApi.createConfig(data);
      set((state) => ({
        configs: [...state.configs, newConfig],
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to create configuration',
        loading: false 
      });
      throw error;
    }
  },

  // Update LLM configuration
  updateConfig: async (id: string, data: LLMConfigUpdate) => {
    set({ loading: true, error: null });
    try {
      const updatedConfig = await llmConfigApi.updateConfig(id, data);
      set((state) => ({
        configs: state.configs.map((config) =>
          config.id === id ? updatedConfig : config
        ),
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to update configuration',
        loading: false 
      });
      throw error;
    }
  },

  // Delete LLM configuration
  deleteConfig: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await llmConfigApi.deleteConfig(id);
      set((state) => ({
        configs: state.configs.filter((config) => config.id !== id),
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to delete configuration',
        loading: false 
      });
      throw error;
    }
  },

  // Test LLM connection
  testConnection: async (id: string): Promise<TestConnectionResult> => {
    set({ loading: true, error: null });
    try {
      const result = await llmConfigApi.testConnection(id);
      set({ loading: false });
      return result;
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Connection test failed',
        loading: false 
      });
      throw error;
    }
  },

  // Fetch all applications
  fetchApplications: async () => {
    set({ loading: true, error: null });
    try {
      const applications = await applicationApi.fetchApplications();
      set({ applications, loading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to fetch applications',
        loading: false 
      });
    }
  },

  // Fetch bindings with optional filter
  fetchBindings: async (applicationId?: string) => {
    set({ loading: true, error: null });
    try {
      const bindings = await bindingApi.fetchBindings(applicationId);
      set({ bindings, loading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to fetch bindings',
        loading: false 
      });
    }
  },

  // Create new binding
  createBinding: async (data: LLMBindingCreate) => {
    set({ loading: true, error: null });
    try {
      const newBinding = await bindingApi.createBinding(data);
      set((state) => ({
        bindings: [...state.bindings, newBinding],
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to create binding',
        loading: false 
      });
      throw error;
    }
  },

  // Update binding
  updateBinding: async (id: string, data: LLMBindingUpdate) => {
    set({ loading: true, error: null });
    try {
      const updatedBinding = await bindingApi.updateBinding(id, data);
      set((state) => ({
        bindings: state.bindings.map((binding) =>
          binding.id === id ? updatedBinding : binding
        ),
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to update binding',
        loading: false 
      });
      throw error;
    }
  },

  // Delete binding
  deleteBinding: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await bindingApi.deleteBinding(id);
      set((state) => ({
        bindings: state.bindings.filter((binding) => binding.id !== id),
        loading: false,
      }));
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to delete binding',
        loading: false 
      });
      throw error;
    }
  },

  // Reorder bindings for drag-and-drop
  reorderBindings: async (applicationId: string, newOrder: string[]) => {
    set({ loading: true, error: null });
    try {
      const state = get();
      const appBindings = state.bindings.filter(
        (b) => b.application.id === applicationId
      );

      // Update priorities based on new order
      const updatePromises = newOrder.map((bindingId, index) => {
        const binding = appBindings.find((b) => b.id === bindingId);
        if (!binding) return Promise.resolve();
        
        const newPriority = index + 1;
        if (binding.priority === newPriority) return Promise.resolve();
        
        return bindingApi.updateBinding(bindingId, { priority: newPriority });
      });

      await Promise.all(updatePromises);
      
      // Refresh bindings to get updated data
      await get().fetchBindings(applicationId);
      
      set({ loading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'Failed to reorder bindings',
        loading: false 
      });
      throw error;
    }
  },

  // Clear error state
  clearError: () => {
    set({ error: null });
  },
}));
