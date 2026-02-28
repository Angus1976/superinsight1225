/**
 * AnnotationActions Component Tests
 *
 * Tests for annotation workflow action buttons:
 * - Next task button (disabled when not labeled)
 * - Skip task button
 * - Manual sync button with loading state
 * - Callback invocations
 *
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnnotationActions } from '../AnnotationActions';
import type { LabelStudioTask } from '@/types/labelStudio';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'annotate.operations': 'Operations',
        'annotate.nextTask': 'Next Task',
        'annotate.skipTask': 'Skip Task',
        'annotate.manualSync': 'Manual Sync',
      };
      return translations[key] || key;
    },
  }),
}));

// ============================================================================
// Test Data
// ============================================================================

const createMockLSTask = (overrides: Partial<LabelStudioTask> = {}): LabelStudioTask => ({
  id: 1,
  data: { text: 'Sample annotation text' },
  project: 10,
  is_labeled: false,
  annotations: [],
  ...overrides,
});

// ============================================================================
// Tests
// ============================================================================

describe('AnnotationActions', () => {
  const mockOnNextTask = vi.fn();
  const mockOnSkipTask = vi.fn();
  const mockOnSyncProgress = vi.fn();

  const defaultProps = {
    currentTask: createMockLSTask(),
    syncInProgress: false,
    onNextTask: mockOnNextTask,
    onSkipTask: mockOnSkipTask,
    onSyncProgress: mockOnSyncProgress,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all three action buttons', () => {
    render(<AnnotationActions {...defaultProps} />);

    expect(screen.getByText('Next Task')).toBeInTheDocument();
    expect(screen.getByText('Skip Task')).toBeInTheDocument();
    expect(screen.getByText('Manual Sync')).toBeInTheDocument();
  });

  it('renders operations card title', () => {
    render(<AnnotationActions {...defaultProps} />);
    expect(screen.getByText('Operations')).toBeInTheDocument();
  });

  it('disables Next Task button when task is not labeled', () => {
    render(<AnnotationActions {...defaultProps} />);
    const nextButton = screen.getByRole('button', { name: /Next Task/i });
    expect(nextButton).toBeDisabled();
  });

  it('enables Next Task button when task is labeled', () => {
    const labeledTask = createMockLSTask({ is_labeled: true });
    render(<AnnotationActions {...defaultProps} currentTask={labeledTask} />);
    const nextButton = screen.getByRole('button', { name: /Next Task/i });
    expect(nextButton).not.toBeDisabled();
  });

  it('calls onNextTask when Next Task button is clicked', async () => {
    const user = userEvent.setup();
    const labeledTask = createMockLSTask({ is_labeled: true });
    render(<AnnotationActions {...defaultProps} currentTask={labeledTask} />);

    await user.click(screen.getByRole('button', { name: /Next Task/i }));
    expect(mockOnNextTask).toHaveBeenCalledTimes(1);
  });

  it('calls onSkipTask when Skip Task button is clicked', async () => {
    const user = userEvent.setup();
    render(<AnnotationActions {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /Skip Task/i }));
    expect(mockOnSkipTask).toHaveBeenCalledTimes(1);
  });

  it('calls onSyncProgress when Manual Sync button is clicked', async () => {
    const user = userEvent.setup();
    render(<AnnotationActions {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /Manual Sync/i }));
    expect(mockOnSyncProgress).toHaveBeenCalledTimes(1);
  });

  it('shows loading state on sync button when syncInProgress is true', () => {
    render(<AnnotationActions {...defaultProps} syncInProgress={true} />);
    const syncButton = screen.getByRole('button', { name: /Manual Sync/i });
    expect(syncButton).toHaveClass('ant-btn-loading');
  });

  it('Skip Task button is always enabled', () => {
    render(<AnnotationActions {...defaultProps} />);
    const skipButton = screen.getByRole('button', { name: /Skip Task/i });
    expect(skipButton).not.toBeDisabled();
  });
});
