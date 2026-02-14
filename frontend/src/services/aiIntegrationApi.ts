/**
 * AI Integration API Service
 * Handles workflow playground and AI gateway operations
 */

import axios from 'axios';

const API_BASE = '/api/v1/ai-integration';

export interface WorkflowDefinition {
  id?: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  dataSource: 'governed' | 'raw';
  createdAt?: string;
}

export interface WorkflowStep {
  id: string;
  type: string;
  name: string;
  config: Record<string, any>;
}

export interface WorkflowExecutionResult {
  id: string;
  workflowId: string;
  dataSource: 'governed' | 'raw';
  status: 'success' | 'failed';
  results: any;
  qualityMetrics: QualityMetrics;
  executionTime: number;
  dataPoints: number;
  createdAt: string;
}

export interface QualityMetrics {
  completeness: number;
  accuracy: number;
  consistency: number;
  confidence: number;
  overallScore: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// Parse natural language to workflow
export const parseWorkflow = async (description: string): Promise<WorkflowDefinition> => {
  const response = await axios.post(`${API_BASE}/workflows/parse`, { description });
  return response.data;
};

// Save workflow
export const saveWorkflow = async (workflow: WorkflowDefinition): Promise<WorkflowDefinition> => {
  const response = await axios.post(`${API_BASE}/workflows`, workflow);
  return response.data;
};

// Execute workflow
export const executeWorkflow = async (
  workflowId: string,
  dataSource: 'governed' | 'raw'
): Promise<WorkflowExecutionResult> => {
  const response = await axios.post(`${API_BASE}/workflows/${workflowId}/execute`, { dataSource });
  return response.data;
};

// Compare workflow results
export const compareWorkflowResults = async (
  workflowId: string
): Promise<{ governed: WorkflowExecutionResult; raw: WorkflowExecutionResult }> => {
  const response = await axios.post(`${API_BASE}/workflows/${workflowId}/compare`);
  return response.data;
};

// Get workflow execution history
export const getWorkflowHistory = async (workflowId: string): Promise<WorkflowExecutionResult[]> => {
  const response = await axios.get(`${API_BASE}/workflows/${workflowId}/history`);
  return response.data;
};

// List workflows
export const listWorkflows = async (): Promise<WorkflowDefinition[]> => {
  const response = await axios.get(`${API_BASE}/workflows`);
  return response.data;
};
