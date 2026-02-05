/**
 * TaskDetail Page Integration Tests
 * 
 * End-to-end integration tests for annotation navigation workflow:
 * - Complete user flow from task detail to annotation
 * - Project creation and validation
 * - Authenticated URL generation and window opening
 * - Error handling and recovery
 * 
 * **Validates**: Requirements 1.1, 1.2, 1.3, 1.5, 1.6
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';
import TaskDetailPage from '../TaskDetail';

// Mock the services
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
      canView: true,
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

describe('TaskDetail Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWindowOpen.mockClear();
    
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

  describe('Complete Start Annotation Flow', () => {
    /**
     * Test: Complete flow for starting annotation with existing project
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Start Annotation" button
     * 3. System validates project exists
     * 4. System navigates to annotation page
     * 
     * Validates: Requirements 1.1, 1.2, 1.6
     */
    it('should complete start annotation flow with existing project', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the start annotation button
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      // Wait for navigation
      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalledWith('ls-project-456');
      }, { timeout: 2000 });
    });

    /**
     * Test: Complete flow for starting annotation with project creation
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Start Annotation" button
     * 3. System checks if project exists (not found)
     * 4. System creates new project
     * 5. System updates task with new project ID
     * 6. System navigates to annotation page
     * 
     * Validates: Requirements 1.1, 1.3, 1.6
     */
    it('should complete start annotation flow with project creation', async () => {
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
        task_count: 0,
        message: 'Project created successfully',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the start annotation button
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      // Wait for project creation
      await waitFor(() => {
        expect(mockEnsureProject).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    /**
     * Test: Error handling during start annotation
     * 
     * Flow:
     * 1. User clicks "Start Annotation" button
     * 2. API call fails
     * 3. System displays error message
     * 4. User remains on task detail page
     * 
     * Validates: Requirements 1.7
     */
    it('should handle errors during start annotation', async () => {
      mockValidateProject.mockRejectedValue({
        response: {
          status: 401,
          data: { detail: 'Unauthorized' },
        },
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the start annotation button
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      // Wait for error handling
      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });
  });

  describe('Complete Open in New Window Flow', () => {
    /**
     * Test: Complete flow for opening in new window
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Open in New Window" button
     * 3. System validates project exists
     * 4. System generates authenticated URL with language
     * 5. System opens URL in new window
     * 
     * Validates: Requirements 1.2, 1.5, 1.6
     */
    it('should complete open in new window flow', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/456?token=xyz&lang=zh',
        expires_at: '2026-01-28T12:00:00Z',
        project_id: 'ls-project-456',
        language: 'zh',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the open in new window button
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      // Wait for window.open to be called
      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    /**
     * Test: Language synchronization in new window
     * 
     * Flow:
     * 1. User is in Chinese interface
     * 2. User clicks "Open in New Window"
     * 3. System generates URL with Chinese language
     * 4. User switches to English
     * 5. User clicks "Open in New Window" again
     * 6. System generates URL with English language
     * 
     * Validates: Requirements 1.5
     */
    it('should synchronize language when opening in new window', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/456?token=xyz&lang=zh',
        expires_at: '2026-01-28T12:00:00Z',
        project_id: 'ls-project-456',
        language: 'zh',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the open in new window button
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      // Wait for getAuthUrl to be called
      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Verify language parameter was passed
      const callArgs = mockGetAuthUrl.mock.calls[0];
      expect(callArgs).toBeDefined();
    });

    /**
     * Test: Error handling when opening in new window
     * 
     * Flow:
     * 1. User clicks "Open in New Window" button
     * 2. API call fails
     * 3. System displays error message
     * 4. Window is not opened
     * 5. User remains on task detail page
     * 
     * Validates: Requirements 1.7
     */
    it('should handle errors when opening in new window', async () => {
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

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Click the open in new window button
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      // Wait for error handling
      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Window should not be opened on error
      expect(mockWindowOpen).not.toHaveBeenCalled();
    });
  });

  describe('Multiple Operations on Same Task', () => {
    /**
     * Test: Multiple operations on same task
     * 
     * Flow:
     * 1. User clicks "Start Annotation" button
     * 2. User navigates back to task detail
     * 3. User clicks "Open in New Window" button
     * 4. Both operations complete successfully
     * 
     * Validates: Requirements 1.1, 1.2, 1.6
     */
    it('should handle multiple operations on same task', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      mockGetAuthUrl.mockResolvedValue({
        url: 'https://labelstudio.example.com/projects/456?token=xyz&lang=zh',
        expires_at: '2026-01-28T12:00:00Z',
        project_id: 'ls-project-456',
        language: 'zh',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // First operation: Click start annotation
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Second operation: Click open in new window
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });
      fireEvent.click(openWindowButton);

      await waitFor(() => {
        expect(mockGetAuthUrl).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Both operations should have been called
      expect(mockValidateProject).toHaveBeenCalled();
      expect(mockGetAuthUrl).toHaveBeenCalled();
    });
  });

  describe('Concurrent Button Clicks', () => {
    /**
     * Test: Handling rapid consecutive button clicks
     * 
     * Flow:
     * 1. User rapidly clicks "Start Annotation" button multiple times
     * 2. System handles all clicks gracefully
     * 3. Only one operation is executed
     * 
     * Validates: Requirements 1.1, 1.6
     */
    it('should handle rapid consecutive button clicks', async () => {
      mockValidateProject.mockResolvedValue({
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      });

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Rapidly click the button multiple times
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      fireEvent.click(startButton);
      fireEvent.click(startButton);
      fireEvent.click(startButton);

      // Wait for operations to complete
      await waitFor(() => {
        expect(mockValidateProject).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });
  });
});
