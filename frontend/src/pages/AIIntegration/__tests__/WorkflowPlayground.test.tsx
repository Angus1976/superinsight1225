/**
 * WorkflowPlayground Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import WorkflowPlayground from '../WorkflowPlayground';
import * as aiIntegrationApi from '../../../services/aiIntegrationApi';

vi.mock('../../../services/aiIntegrationApi');

const mockWorkflow = {
  id: 'wf-1',
  name: 'Test Workflow',
  description: 'Test workflow description',
  steps: [
    { id: 's1', type: 'query', name: 'Query Data', config: {} },
    { id: 's2', type: 'transform', name: 'Transform', config: {} },
  ],
  dataSource: 'governed' as const,
};

const mockResult = {
  id: 'r-1',
  workflowId: 'wf-1',
  dataSource: 'governed' as const,
  status: 'success' as const,
  results: {},
  qualityMetrics: {
    completeness: 0.9,
    accuracy: 0.85,
    consistency: 0.88,
    confidence: 0.92,
    overallScore: 0.89,
  },
  executionTime: 1500,
  dataPoints: 100,
  createdAt: new Date().toISOString(),
};

describe('WorkflowPlayground', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the playground with all panels', () => {
    render(<WorkflowPlayground />);
    
    expect(screen.getByText(/workflow playground/i)).toBeInTheDocument();
    expect(screen.getByText(/conversational design/i)).toBeInTheDocument();
    expect(screen.getByText(/workflow definition/i)).toBeInTheDocument();
    expect(screen.getByText(/execution results/i)).toBeInTheDocument();
  });

  it('generates workflow from chat message', async () => {
    vi.mocked(aiIntegrationApi.parseWorkflow).mockResolvedValue(mockWorkflow);
    
    render(<WorkflowPlayground />);
    
    const input = screen.getByPlaceholderText(/describe the data workflow/i);
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(input, { target: { value: 'Create a sentiment analysis workflow' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(aiIntegrationApi.parseWorkflow).toHaveBeenCalledWith('Create a sentiment analysis workflow');
    });
    
    await waitFor(() => {
      expect(screen.getByText('Test Workflow')).toBeInTheDocument();
    });
  });

  it('executes workflow and displays results', async () => {
    vi.mocked(aiIntegrationApi.parseWorkflow).mockResolvedValue(mockWorkflow);
    vi.mocked(aiIntegrationApi.executeWorkflow).mockResolvedValue(mockResult);
    
    render(<WorkflowPlayground />);
    
    // Generate workflow first
    const input = screen.getByPlaceholderText(/describe the data workflow/i);
    fireEvent.change(input, { target: { value: 'Test workflow' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Test Workflow')).toBeInTheDocument();
    });
    
    // Execute workflow
    const executeButton = screen.getByRole('button', { name: /execute/i });
    fireEvent.click(executeButton);
    
    await waitFor(() => {
      expect(aiIntegrationApi.executeWorkflow).toHaveBeenCalledWith('wf-1', 'governed');
    });
    
    await waitFor(() => {
      expect(screen.getByText(/89/)).toBeInTheDocument(); // Quality score
    });
  });

  it('saves workflow to production', async () => {
    vi.mocked(aiIntegrationApi.parseWorkflow).mockResolvedValue(mockWorkflow);
    vi.mocked(aiIntegrationApi.saveWorkflow).mockResolvedValue(mockWorkflow);
    
    render(<WorkflowPlayground />);
    
    // Generate workflow
    const input = screen.getByPlaceholderText(/describe the data workflow/i);
    fireEvent.change(input, { target: { value: 'Test workflow' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Test Workflow')).toBeInTheDocument();
    });
    
    // Save workflow
    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(aiIntegrationApi.saveWorkflow).toHaveBeenCalledWith(mockWorkflow);
    });
  });

  it('toggles between governed and raw data sources', async () => {
    vi.mocked(aiIntegrationApi.parseWorkflow).mockResolvedValue(mockWorkflow);
    
    render(<WorkflowPlayground />);
    
    // Generate workflow
    const input = screen.getByPlaceholderText(/describe the data workflow/i);
    fireEvent.change(input, { target: { value: 'Test workflow' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Test Workflow')).toBeInTheDocument();
    });
    
    // Toggle to raw data
    const rawButton = screen.getByRole('radio', { name: /raw data/i });
    fireEvent.click(rawButton);
    
    expect(rawButton).toBeChecked();
  });
});
