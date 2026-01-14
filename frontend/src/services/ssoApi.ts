/**
 * SSO API Service for SuperInsight Platform
 * 
 * Provides API client functions for Single Sign-On management.
 */

import apiClient from './api/client';

// ============================================================================
// Types
// ============================================================================

export type SSOProtocol = 'saml' | 'oauth2' | 'oidc' | 'ldap';

export interface SSOProviderConfig {
  // SAML fields
  entity_id?: string;
  idp_metadata_url?: string;
  idp_sso_url?: string;
  idp_certificate?: string;
  
  // OAuth2/OIDC fields
  client_id?: string;
  client_secret?: string;
  authorization_url?: string;
  token_url?: string;
  userinfo_url?: string;
  scopes?: string[];
  
  // LDAP fields
  server_url?: string;
  bind_dn?: string;
  bind_password?: string;
  base_dn?: string;
  user_search_filter?: string;
}

export interface SSOProvider {
  id: string;
  name: string;
  protocol: SSOProtocol;
  enabled: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CreateSSOProviderRequest {
  name: string;
  protocol: SSOProtocol;
  config: SSOProviderConfig;
  enabled?: boolean;
}

export interface UpdateSSOProviderRequest {
  config?: SSOProviderConfig;
  enabled?: boolean;
}

export interface SSOLoginInitResponse {
  redirect_url: string;
  state?: string;
  provider_name: string;
}

export interface SSOLoginResponse {
  success: boolean;
  session_id?: string;
  user_id?: string;
  email?: string;
  error?: string;
}

export interface SSOLogoutResponse {
  success: boolean;
  redirect_url?: string;
  error?: string;
}

export interface SSOTestResponse {
  success: boolean;
  message?: string;
  error?: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/api/v1/sso';

export const ssoApi = {
  // Provider Management
  async createProvider(data: CreateSSOProviderRequest): Promise<SSOProvider> {
    const response = await apiClient.post<SSOProvider>(`${BASE_URL}/providers`, data);
    return response.data;
  },

  async listProviders(enabledOnly?: boolean): Promise<SSOProvider[]> {
    const response = await apiClient.get<SSOProvider[]>(`${BASE_URL}/providers`, {
      params: { enabled_only: enabledOnly },
    });
    return response.data;
  },

  async getProvider(providerName: string): Promise<SSOProvider> {
    const response = await apiClient.get<SSOProvider>(
      `${BASE_URL}/providers/${providerName}`
    );
    return response.data;
  },

  async updateProvider(
    providerName: string,
    data: UpdateSSOProviderRequest
  ): Promise<SSOProvider> {
    const response = await apiClient.put<SSOProvider>(
      `${BASE_URL}/providers/${providerName}`,
      data
    );
    return response.data;
  },

  async deleteProvider(providerName: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/providers/${providerName}`);
  },

  // SSO Login/Logout
  async initiateLogin(
    providerName: string,
    redirectUri: string,
    state?: string
  ): Promise<SSOLoginInitResponse> {
    const response = await apiClient.get<SSOLoginInitResponse>(
      `${BASE_URL}/login/${providerName}`,
      { params: { redirect_uri: redirectUri, state } }
    );
    return response.data;
  },

  async handleCallback(
    providerName: string,
    callbackData: Record<string, string>
  ): Promise<SSOLoginResponse> {
    const response = await apiClient.post<SSOLoginResponse>(
      `${BASE_URL}/callback/${providerName}`,
      callbackData
    );
    return response.data;
  },

  async logout(
    currentUserId: string,
    providerName?: string,
    sessionId?: string
  ): Promise<SSOLogoutResponse> {
    const response = await apiClient.post<SSOLogoutResponse>(
      `${BASE_URL}/logout`,
      { provider_name: providerName, session_id: sessionId },
      { params: { current_user_id: currentUserId } }
    );
    return response.data;
  },

  // Provider Testing
  async testProvider(providerName: string): Promise<SSOTestResponse> {
    const response = await apiClient.post<SSOTestResponse>(
      `${BASE_URL}/providers/${providerName}/test`
    );
    return response.data;
  },

  async enableProvider(providerName: string): Promise<SSOProvider> {
    const response = await apiClient.post<SSOProvider>(
      `${BASE_URL}/providers/${providerName}/enable`
    );
    return response.data;
  },

  async disableProvider(providerName: string): Promise<SSOProvider> {
    const response = await apiClient.post<SSOProvider>(
      `${BASE_URL}/providers/${providerName}/disable`
    );
    return response.data;
  },
};

export default ssoApi;
