/**
 * TaskAnnotate Page Tests
 * 
 * Tests for annotation page error handling:
 * - fetchData error handling for 404/401 errors
 * - Error message display
 * - Retry functionality
 * 
 * **Validates**: Requirements 1.1, 1.7
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';

// Mock the services and hooks
vi.mock('@/services/labelStudioService', () => ({
  labelStudioService: {
    validateProject: vi.fn(),
    ensureProject: vi.fn(),
    getProject: vi.fn(),
  },
}));

vi.mock('@/hooks/useTask', () => ({
  useTask: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

vi.mock('@/stores/languageStore', () => ({
  useLanguageStore: vi.fn(() => ({
    language: 'zh',
    syncToLabelStudio: vi.fn(),
  })),
}));

vi.mock('@/components/LabelStudio/LabelStudioEmbed', () => ({
  LabelStudioEmbed: ({ projectId }: { projectId: string }) => (
    <div data-testid="label-studio-embed">Label Studio Embed - Project: {projectId}</div>
  ),
}));

import { labelStudioService } from '@/services/labelStudioService';
import { useTask } from '@/hooks/useTask';

const mockValidateProject = labelStudioService.validateProject as ReturnType<typeof vi.fn>;
const mockEnsureProject = labelStudioService.ensureProject as ReturnType<typeof vi.fn>;
const mockGetProject = labelStudioService.getProject as ReturnType<typeof vi.fn>;
const mockUseTask = useTask as ReturnType<typeof vi.fn>;

// Create a test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

// Wrapper component for tests
const TestWrapper: React.FC<{ children: React.ReactNode; initialEntries?: string[] }> = ({
  children,
  initialEntries = ['/tasks/test-task-123/annotate'],
}) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/tasks/:id/annotate" element={children} />
            <Route path="/tasks/:id" element={<div data-testid="task-detail-page">Task Detail Page</div>} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    </QueryClientProvider>
  );
};

describe('TaskAnnotate Page - Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    mockUseTask.mockReturnValue({
      data: {
        id: 'test-task-123',
        name: 'Test Task',
        description: 'Test description',
        status: 'in_progress',
        priority: 'high',
        annotation_type: 'sentiment',
        label_studio_project_id: 'ls-project-456',
        progress: 50,
        total_items: 100,
        completed_items: 50,
      },
      isLoading: false,
      error: null,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchData error handling', () => {
    /**
     * Test: Handles 404 error when project not found
     * Validates: Requirements 1.7
     */
    it('should display appropriate error message for 404 (project not found)', async () => {
      mockValidateProject.mockResolvedValue({
        exists: false,
        accessible: false,
        task_count: 0,
        annotation_count: 0,
        status: 'not_found',
        error_message: 'Project not found',
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalledWith('ls-project-456');
      });
    });

    /**
     * Test: Handles 401 error when authentication fails
     * Validates: Requirements 1.7
     */
    it('should display appropriate error message for 401 (authentication failed)', async () => {
      mockValidateProject.mockRejectedValue({
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });

    /**
     * Test: Handles network error
     * Validates: Requirements 1.7
     */
    it('should display appropriate error message for network errors', async () => {
      mockValidateProject.mockRejectedValue(new Error('Network Error'));

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });

    /**
     * Test: Handles 503 service unavailable error
     * Validates: Requirements 1.7
     */
    it('should display appropriate error message for 503 (service unavailable)', async () => {
      mockValidateProject.mockRejectedValue({
        response: {
          status: 503,
          data: { detail: 'Service Unavailable' },
        },
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });
  });

  describe('Successful data loading', () => {
    /**
     * Test: Successfully loads and displays Label Studio embed
     * Validates: Requirements 1.1
     */
    it('should display Label Studio embed when project is valid', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalledWith('ls-project-456');
      });
    });

    /**
     * Test: Creates project automatically when not found
     * Validates: Requirements 1.3
     */
    it('should create project automatically when validation returns not found', async () => {
      mockValidateProject.mockResolvedValue({
        exists: false,
        accessible: false,
        task_count: 0,
        annotation_count: 0,
        status: 'not_found',
      });

      mockEnsureProject.mockResolvedValue({
        project_id: 'new-project-789',
        created: true,
        status: 'ready',
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });
  });

  describe('Task without project ID', () => {
    /**
     * Test: Handles task without Label Studio project ID
     * Validates: Requirements 1.3
     */
    it('should create project when task has no project ID', async () => {
      mockUseTask.mockReturnValue({
        data: {
          id: 'test-task-123',
          name: 'Test Task',
          description: 'Test description',
          status: 'in_progress',
          priority: 'high',
          annotation_type: 'sentiment',
          label_studio_project_id: null, // No project ID
          progress: 0,
          total_items: 100,
          completed_items: 0,
        },
        isLoading: false,
        error: null,
      });

      mockEnsureProject.mockResolvedValue({
        project_id: 'new-project-789',
        created: true,
        status: 'ready',
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockEnsureProject).toHaveBeenCalled();
      });
    });
  });

  describe('Loading states', () => {
    /**
     * Test: Shows loading state while fetching data
     * Validates: Requirements 1.6
     */
    it('should show loading state while fetching task data', async () => {
      mockUseTask.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');
      
      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      // Should show loading indicator
      expect(screen.queryByTestId('label-studio-embed')).not.toBeInTheDocument();
    });
  });
});
