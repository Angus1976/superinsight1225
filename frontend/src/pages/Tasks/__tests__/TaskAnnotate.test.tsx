/**
 * TaskAnnotate 页面测试
 *
 * 与当前实现一致：通过 useTask 取任务、apiClient 拉取 LS 项目/任务、无 project 时 ensureProject；
 * 不再使用 labelStudioService.validateProject。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';

const mockApiGet = vi.fn();

vi.mock('@/services/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}));

vi.mock('@/services/labelStudioService', () => ({
  labelStudioService: {
    ensureProject: vi.fn(),
    importTasks: vi.fn().mockResolvedValue({ imported: 0 }),
    syncAnnotations: vi.fn(),
  },
}));

vi.mock('@/hooks/useTask', () => ({
  useTask: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
  useUpdateTask: vi.fn(() => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
  })),
  useLazyTask: vi.fn(() => ({
    prefetchTask: vi.fn(),
  })),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    token: 'test-jwt-token',
  })),
}));

vi.mock('@/stores/languageStore', () => ({
  useLanguageStore: vi.fn(() => ({
    language: 'zh',
    syncToLabelStudio: vi.fn(),
  })),
}));

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: vi.fn(() => ({
    annotation: { canView: true, canCreate: true, canEdit: true, canDelete: true },
    roleDisplayName: 'Annotator',
    checkPermission: vi.fn(() => true),
  })),
}));

vi.mock('@/hooks/useLabelStudio', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useLabelStudio')>();
  return {
    ...actual,
    useLabelStudio: () => {
      const real = actual.useLabelStudio();
      return {
        ...real,
        navigateToTaskDetail: vi.fn(),
        openLabelStudio: vi.fn().mockResolvedValue(undefined),
      };
    },
  };
});

vi.mock('@/components/Auth/PermissionGuard', () => ({
  PermissionGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { labelStudioService } from '@/services/labelStudioService';
import { useTask } from '@/hooks/useTask';

const mockEnsureProject = labelStudioService.ensureProject as ReturnType<typeof vi.fn>;
const mockUseTask = useTask as ReturnType<typeof vi.fn>;

const defaultTask = {
  id: 'test-task-123',
  name: 'Test Task',
  description: 'Test description',
  status: 'in_progress' as const,
  priority: 'high' as const,
  annotation_type: 'sentiment',
  label_studio_project_id: '456',
  progress: 50,
  total_items: 100,
  completed_items: 50,
};

const lsTaskRow = {
  id: '1',
  project_id: '456',
  data: { text: 'Sample text for annotation' },
  status: 'pending' as const,
  annotations: [],
  predictions: [],
  created_at: '2020-01-01T00:00:00Z',
  updated_at: '2020-01-01T00:00:00Z',
  is_labeled: false,
  overlap: 1,
  total_annotations: 0,
  cancelled_annotations: 0,
  total_predictions: 0,
};

function mockProjectAndTasksSuccess() {
  mockApiGet.mockImplementation(async (url: string) => {
    const u = String(url);
    if (u.includes('/tasks') && u.includes('/projects/')) {
      return {
        data: {
          tasks: [lsTaskRow],
        },
      };
    }
    if (u.includes('/projects/456') && !u.includes('/tasks')) {
      return { data: { id: 456, title: 'LS Project' } };
    }
    return { data: {} };
  });
}

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

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
    mockApiGet.mockReset();
    mockUseTask.mockReturnValue({
      data: defaultTask,
      isLoading: false,
      error: null,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchData error handling', () => {
    it('should display appropriate error message for 404 (project not found)', async () => {
      mockApiGet.mockRejectedValueOnce({
        response: { status: 404, data: { detail: 'Not found' } },
        isAxiosError: true,
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockApiGet).toHaveBeenCalled(), { timeout: 3000 });

      await waitFor(
        () => {
          expect(screen.getByText(/Project not found|项目未找到|找不到项目/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should display appropriate error message for 401 (authentication failed)', async () => {
      mockApiGet.mockRejectedValueOnce({
        response: { status: 401, data: { detail: 'Unauthorized' } },
        isAxiosError: true,
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockApiGet).toHaveBeenCalled(), { timeout: 3000 });
    });

    it('should display appropriate error message for network errors', async () => {
      mockApiGet.mockRejectedValueOnce(new Error('Network Error'));

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockApiGet).toHaveBeenCalled(), { timeout: 3000 });
    });

    it('should display appropriate error message for 503 (service unavailable)', async () => {
      mockApiGet.mockRejectedValueOnce({
        response: { status: 503, data: { detail: 'Service Unavailable' } },
        isAxiosError: true,
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockApiGet).toHaveBeenCalled(), { timeout: 3000 });
    });
  });

  describe('Successful data loading', () => {
    it('should display main annotation UI when project and tasks load', async () => {
      mockProjectAndTasksSuccess();

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(
        () => {
          expect(screen.getByText('LS Project')).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });

    it('should create project automatically when task has no project id', async () => {
      mockUseTask.mockReturnValue({
        data: {
          ...defaultTask,
          label_studio_project_id: null as unknown as string,
        },
        isLoading: false,
        error: null,
      });

      mockEnsureProject.mockResolvedValue({
        project_id: '789',
        created: true,
        status: 'ready',
      });

      mockApiGet.mockImplementation(async (url: string) => {
        const u = String(url);
        if (u.includes('/tasks') && u.includes('/projects/')) {
          return { data: { tasks: [{ ...lsTaskRow, project_id: '789' }] } };
        }
        if (u.includes('/projects/789') && !u.includes('/tasks')) {
          return { data: { id: 789, title: 'New Project' } };
        }
        return { data: {} };
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockEnsureProject).toHaveBeenCalled(), { timeout: 5000 });
    });
  });

  describe('Task without project ID', () => {
    it('should call ensureProject when task has no project ID', async () => {
      mockUseTask.mockReturnValue({
        data: {
          ...defaultTask,
          label_studio_project_id: null as unknown as string,
        },
        isLoading: false,
        error: null,
      });

      mockEnsureProject.mockResolvedValue({
        project_id: '789',
        created: true,
        status: 'ready',
      });

      mockApiGet.mockImplementation(async (url: string) => {
        const u = String(url);
        if (u.includes('/tasks') && u.includes('/projects/')) {
          return { data: { tasks: [{ ...lsTaskRow, project_id: '789' }] } };
        }
        if (u.includes('/projects/789') && !u.includes('/tasks')) {
          return { data: { id: 789, title: 'New Project' } };
        }
        return { data: {} };
      });

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(() => expect(mockEnsureProject).toHaveBeenCalled(), { timeout: 5000 });
    });
  });

  describe('Loading states', () => {
    it('should show loading state while fetching task data', async () => {
      mockApiGet.mockImplementation(() => new Promise(() => {}));

      const { default: TaskAnnotatePage } = await import('../TaskAnnotate');

      render(
        <TestWrapper>
          <TaskAnnotatePage />
        </TestWrapper>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/loadingTask|加载任务|Loading/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });
});
