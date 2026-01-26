/**
 * TaskDetail Page Tests
 * 
 * Tests for annotation workflow button handlers:
 * - handleStartAnnotation: Validates project and navigates to annotation page
 * - handleOpenInNewWindow: Gets authenticated URL and opens in new window
 * 
 * **Validates**: Requirements 1.1, 1.2, 1.5, 1.6
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';

// Mock the services and hooks
vi.mock('@/services/labelStudioService', () => ({
  labelStudioService: {
    validateProject: vi.fn(),
    ensureProject: vi.fn(),
    getAuthUrl: vi.fn(),
  },
}));

vi.mock('@/hooks/useTask', () => ({
  useTask: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
  useUpdateTask: vi.fn(() => ({
    mutateAsync: vi.fn(),
  })),
  useDeleteTask: vi.fn(() => ({
    mutateAsync: vi.fn(),
  })),
}));

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: vi.fn(() => ({
    annotation: {
      canCreate: true,
      canEdit: true,
      canDelete: true,
    },
  })),
}));

vi.mock('@/stores/languageStore', () => ({
  useLanguageStore: vi.fn(() => ({
    language: 'zh',
  })),
}));

vi.mock('@/components/Tasks', () => ({
  ProgressTracker: () => <div data-testid="progress-tracker">Progress Tracker</div>,
}));

import { labelStudioService } from '@/services/labelStudioService';
import { useTask, useUpdateTask } from '@/hooks/useTask';
import { useLanguageStore } from '@/stores/languageStore';

const mockValidateProject = labelStudioService.validateProject as ReturnType<typeof vi.fn>;
const mockEnsureProject = labelStudioService.ensureProject as ReturnType<typeof vi.fn>;
const mockGetAuthUrl = labelStudioService.getAuthUrl as ReturnType<typeof vi.fn>;
const mockUseTask = useTask as ReturnType<typeof vi.fn>;
const mockUseUpdateTask = useUpdateTask as ReturnType<typeof vi.fn>;
const mockUseLanguageStore = useLanguageStore as ReturnType<typeof vi.fn>;

// Mock window.open
const mockWindowOpen = vi.fn();
Object.defineProperty(window, 'open', {
  value: mockWindowOpen,
  writable: true,
});

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
  initialEntries = ['/tasks/test-task-123'],
}) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/tasks/:id" element={children} />
            <Route path="/tasks/:id/annotate" element={<div data-testid="annotate-page">Annotate Page</div>} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    </QueryClientProvider>
  );
};

describe('TaskDetail Page - Annotation Button Handlers', () => {
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
    
    mockUseUpdateTask.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    });
    
    mockUseLanguageStore.mockReturnValue({
      language: 'zh',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('handleStartAnnotation', () => {
    /**
     * Test: Successful navigation when project exists and is accessible
     * Validates: Requirements 1.1, 1.6
     */
    it('should navigate to annotation page when project exists and is accessible', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      // Import and render the component
      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Find and click the start annotation button
      const startButton = await screen.findByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      // Wait for validation and navigation
      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalledWith('ls-project-456');
      });
    });

    /**
     * Test: Creates project when it doesn't exist
     * Validates: Requirements 1.3
     */
    it('should create project when it does not exist', async () => {
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

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const startButton = await screen.findByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockEnsureProject).toHaveBeenCalledWith({
          task_id: 'test-task-123',
          task_name: expect.any(String),
          annotation_type: 'sentiment',
        });
      });
    });

    /**
     * Test: Handles authentication error
     * Validates: Requirements 1.7
     */
    it('should show error message on authentication failure', async () => {
      mockValidateProject.mockRejectedValue({
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const startButton = await screen.findByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });

    /**
     * Test: Handles service unavailable error
     * Validates: Requirements 1.7
     */
    it('should show error message when service is unavailable', async () => {
      mockValidateProject.mockRejectedValue({
        response: {
          status: 503,
          data: { detail: 'Service Unavailable' },
        },
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const startButton = await screen.findByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      });
    });
  });

  describe('handleOpenInNewWindow', () => {
    /**
     * Test: Opens Label Studio in new window with authenticated URL
     * Validates: Requirements 1.2, 1.5
     */
    it('should open Label Studio in new window with authenticated URL', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/456?token=abc123&lang=zh',
        expires_at: '2025-01-20T15:00:00Z',
        project_id: 'ls-project-456',
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const openWindowButton = await screen.findByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalledWith('ls-project-456', 'zh');
      });

      await waitFor(() => {
        expect(mockWindowOpen).toHaveBeenCalledWith(
          'https://labelstudio.example.com/projects/456?token=abc123&lang=zh',
          '_blank',
          'noopener,noreferrer'
        );
      });
    });

    /**
     * Test: Uses correct language parameter based on user preference
     * Validates: Requirements 1.5
     */
    it('should use English language parameter when user prefers English', async () => {
      mockUseLanguageStore.mockReturnValue({
        language: 'en',
      });

      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/456?token=abc123&lang=en',
        expires_at: '2025-01-20T15:00:00Z',
        project_id: 'ls-project-456',
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const openWindowButton = await screen.findByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalledWith('ls-project-456', 'en');
      });
    });

    /**
     * Test: Creates project if it doesn't exist before opening
     * Validates: Requirements 1.3
     */
    it('should create project before opening if it does not exist', async () => {
      // Task without project ID
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

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/789?token=xyz789&lang=zh',
        expires_at: '2025-01-20T15:00:00Z',
        project_id: 'new-project-789',
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const openWindowButton = await screen.findByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      await waitFor(() => {
        expect(mockEnsureProject).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalledWith('new-project-789', 'zh');
      });
    });

    /**
     * Test: Handles error when getting authenticated URL fails
     * Validates: Requirements 1.7
     */
    it('should handle error when getting authenticated URL fails', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockRejectedValue({
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' },
        },
      });

      const { default: TaskDetailPage } = await import('../TaskDetail');
      
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      const openWindowButton = await screen.findByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalled();
      });

      // Window should not be opened on error
      expect(mockWindowOpen).not.toHaveBeenCalled();
    });
  });
});
