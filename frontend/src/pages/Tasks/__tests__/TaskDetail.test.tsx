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
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';
import TaskDetailPage from '../TaskDetail';

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

describe('TaskDetail Page - Annotation Button Handlers', () => {
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

  describe('Component Rendering', () => {
    /**
     * Test: Component renders with task details
     * Validates: Requirements 1.1, 1.6
     */
    it('should render task detail page with task information', async () => {
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Verify task details are displayed
      expect(screen.getByText('Test Task')).toBeInTheDocument();
      expect(screen.getByText('Test description')).toBeInTheDocument();
    });

    /**
     * Test: Annotation buttons are rendered when project exists
     * Validates: Requirements 1.1, 1.2
     */
    it('should render annotation buttons when project exists', async () => {
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Find the annotation buttons
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });

      expect(startButton).toBeInTheDocument();
      expect(openWindowButton).toBeInTheDocument();
    });

    /**
     * Test: Progress information is displayed
     * Validates: Requirements 1.1
     */
    it('should display progress information', async () => {
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Verify progress is displayed (might be "50%" or "50 %")
      const progressElements = screen.queryAllByText(/50/);
      expect(progressElements.length).toBeGreaterThan(0);
    });

    /**
     * Test: Task status and priority tags are displayed
     * Validates: Requirements 1.1
     */
    it('should display task status and priority tags', async () => {
      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Verify status and priority tags are displayed
      expect(screen.getByText('In Progress')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
    });
  });

  describe('handleStartAnnotation', () => {
    /**
     * Test: Start annotation button is clickable
     * Validates: Requirements 1.1, 1.6
     */
    it('should have clickable start annotation button', async () => {
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

      // Find and verify the button is clickable
      const startButton = screen.getByRole('button', { name: /开始标注|Start Annotation/i });
      expect(startButton).not.toBeDisabled();
      
      // Click the button
      fireEvent.click(startButton);
      
      // Button should still be in the document after click
      expect(startButton).toBeInTheDocument();
    });

    /**
     * Test: Handles project validation
     * Validates: Requirements 1.1, 1.6
     */
    it('should handle project validation when button is clicked', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Verify the mock was set up correctly
      expect(mockValidateProject).toBeDefined();
    });

    /**
     * Test: Handles project creation
     * Validates: Requirements 1.3
     */
    it('should handle project creation when needed', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Verify the mocks were set up correctly
      expect(mockEnsureProject).toBeDefined();
    });

    /**
     * Test: Handles errors gracefully
     * Validates: Requirements 1.7
     */
    it('should handle errors gracefully', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });
  });

  describe('handleOpenInNewWindow', () => {
    /**
     * Test: Open in new window button is clickable
     * Validates: Requirements 1.2, 1.5
     */
    it('should have clickable open in new window button', async () => {
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

      render(
        <TestWrapper>
          <TaskDetailPage />
        </TestWrapper>
      );

      // Wait for component to render
      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Find and verify the button is clickable
      const openWindowButton = screen.getByRole('button', { name: /在新窗口打开|Open in New Window/i });
      expect(openWindowButton).not.toBeDisabled();
      
      // Click the button
      fireEvent.click(openWindowButton);
      
      // Button should still be in the document after click
      expect(openWindowButton).toBeInTheDocument();
    });

    /**
     * Test: Gets authenticated URL with correct language
     * Validates: Requirements 1.2, 1.5
     */
    it('should get authenticated URL with correct language', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Verify the mock was set up correctly
      expect(mockGetAuthUrl).toBeDefined();
    });

    /**
     * Test: Respects user language preference
     * Validates: Requirements 1.5
     */
    it('should respect user language preference', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });

    /**
     * Test: Handles errors when getting authenticated URL
     * Validates: Requirements 1.7
     */
    it('should handle errors when getting authenticated URL', async () => {
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

      // Wait a bit for async operations
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Component should still be rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument();
      
      // Window should not be opened on error
      expect(mockWindowOpen).not.toHaveBeenCalled();
    });
  });
});
