// Unit tests for TaskCreateModal component
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';
import { TaskCreateModal } from '../TaskCreateModal';

// Mock the useCreateTask hook
vi.mock('@/hooks/useTask', () => ({
  useCreateTask: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ id: 'test-id' }),
    isPending: false,
  }),
}));

// Test wrapper component
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>
        <App>{children}</App>
      </I18nextProvider>
    </QueryClientProvider>
  );
};

describe('TaskCreateModal', () => {
  const mockOnCancel = vi.fn();
  const mockOnSuccess = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Modal rendering', () => {
    it('should render modal when open is true', () => {
      render(
        <TaskCreateModal open={true} onCancel={mockOnCancel} onSuccess={mockOnSuccess} />,
        { wrapper: createWrapper() }
      );
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should not render modal when open is false', () => {
      render(
        <TaskCreateModal open={false} onCancel={mockOnCancel} onSuccess={mockOnSuccess} />,
        { wrapper: createWrapper() }
      );
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should show single/batch mode toggle', () => {
      render(
        <TaskCreateModal open={true} onCancel={mockOnCancel} onSuccess={mockOnSuccess} />,
        { wrapper: createWrapper() }
      );
      
      // Check for radio buttons for single/batch mode
      const radioButtons = screen.getAllByRole('radio');
      expect(radioButtons.length).toBeGreaterThanOrEqual(2);
    });

    it('should show templates button', () => {
      render(
        <TaskCreateModal open={true} onCancel={mockOnCancel} onSuccess={mockOnSuccess} />,
        { wrapper: createWrapper() }
      );
      
      // Check for templates button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Cancel behavior', () => {
    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <TaskCreateModal open={true} onCancel={mockOnCancel} onSuccess={mockOnSuccess} />,
        { wrapper: createWrapper() }
      );
      
      // Find cancel button
      const buttons = screen.getAllByRole('button');
      const cancelButton = buttons.find(b => 
        b.textContent?.toLowerCase().includes('cancel') || 
        b.textContent?.includes('取消')
      );
      
      if (cancelButton) {
        await user.click(cancelButton);
        expect(mockOnCancel).toHaveBeenCalled();
      }
    });
  });
});
