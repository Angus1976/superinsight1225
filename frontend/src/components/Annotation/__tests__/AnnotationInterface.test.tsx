/**
 * AnnotationInterface Component Tests
 *
 * Tests for the main annotation editor including:
 * - Component rendering with task data
 * - Annotation toolbar (undo/redo, status tags)
 * - Form validation (required sentiment field)
 * - Annotation submission (save/update)
 * - Quick annotation buttons
 * - Permission-based access control
 * - Loading state
 *
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { AnnotationInterface } from '../AnnotationInterface';

// Mock usePermissions hook
const mockPermissions = {
  annotation: { canView: true, canCreate: true, canEdit: true, canDelete: false },
  roleDisplayName: 'Annotator',
};

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => mockPermissions,
}));

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'interface.loading': 'Loading...',
        'interface.toolbar.undo': 'Undo',
        'interface.toolbar.redo': 'Redo',
        'interface.toolbar.history': 'History',
        'interface.status.labeled': 'Labeled',
        'interface.status.unlabeled': 'Unlabeled',
        'interface.status.readOnly': 'Read Only',
        'interface.content.title': 'Content',
        'interface.tools.title': 'Annotation Tools',
        'interface.tools.saveAnnotation': 'Save Annotation',
        'interface.sentiment.title': 'Sentiment',
        'interface.sentiment.required': 'Please select a sentiment',
        'interface.sentiment.positiveLabel': 'Positive',
        'interface.sentiment.negativeLabel': 'Negative',
        'interface.sentiment.neutralLabel': 'Neutral',
        'interface.sentiment.positive': 'Positive',
        'interface.sentiment.negative': 'Negative',
        'interface.sentiment.neutral': 'Neutral',
        'interface.quickAnnotation.title': 'Quick Annotation',
        'interface.rating.title': 'Rating',
        'interface.comment.title': 'Comment',
        'interface.comment.placeholder': 'Enter comment...',
        'interface.currentResult.title': 'Current Result',
        'interface.currentResult.sentiment': 'Sentiment',
        'interface.currentResult.rating': 'Rating',
        'interface.currentResult.comment': 'Comment',
        'interface.messages.saveSuccess': 'Annotation saved successfully',
        'interface.messages.saveError': 'Failed to save annotation',
        'interface.messages.noCreatePermission': 'No permission to create annotations',
        'interface.messages.noEditPermission': 'No permission to edit annotations',
      };
      return translations[key] || key;
    },
  }),
}));

// ============================================================================
// Test Data
// ============================================================================

const createMockProject = () => ({
  id: 1,
  title: 'Test Project',
  description: 'A test project',
  label_config: '<View><Text name="text" value="$text"/></View>',
});

const createMockTask = (overrides = {}) => ({
  id: 100,
  data: { text: 'This is a sample text for annotation.' },
  annotations: [],
  is_labeled: false,
  ...overrides,
});

const createMockAnnotation = (overrides = {}) => ({
  id: 1,
  result: [
    {
      value: { choices: ['Positive'] },
      from_name: 'sentiment',
      to_name: 'text',
      type: 'choices',
    },
  ],
  task: 100,
  ...overrides,
});

// ============================================================================
// Rendering Tests
// ============================================================================

describe('AnnotationInterface - Rendering', () => {
  const defaultProps = {
    project: createMockProject(),
    task: createMockTask(),
    onAnnotationSave: vi.fn(),
    onAnnotationUpdate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissions.annotation = { canView: true, canCreate: true, canEdit: true, canDelete: false };
    mockPermissions.roleDisplayName = 'Annotator';
  });

  it('renders task text content', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('This is a sample text for annotation.')).toBeInTheDocument();
  });

  it('renders content and tools panels', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(screen.getByText('Annotation Tools')).toBeInTheDocument();
  });

  it('renders sentiment radio options', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('Positive', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Negative', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Neutral', { selector: 'span' })).toBeInTheDocument();
  });

  it('renders rating options (1-5)', () => {
    render(<AnnotationInterface {...defaultProps} />);
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(String(i))).toBeInTheDocument();
    }
  });

  it('renders comment textarea', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByPlaceholderText('Enter comment...')).toBeInTheDocument();
  });

  it('shows loading state when loading prop is true', () => {
    render(<AnnotationInterface {...defaultProps} loading={true} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('shows unlabeled tag for unlabeled task', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('Unlabeled')).toBeInTheDocument();
  });

  it('shows labeled tag for labeled task', () => {
    const labeledTask = createMockTask({ is_labeled: true });
    render(<AnnotationInterface {...defaultProps} task={labeledTask} />);
    expect(screen.getByText('Labeled')).toBeInTheDocument();
  });

  it('displays role name tag', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('Annotator')).toBeInTheDocument();
  });

  it('populates form with existing annotation data', () => {
    const taskWithAnnotation = createMockTask({
      annotations: [createMockAnnotation()],
    });
    render(<AnnotationInterface {...defaultProps} task={taskWithAnnotation} />);
    // The form should be populated - the radio for "Positive" should be checked
    const radios = screen.getAllByRole('radio');
    const positiveRadio = radios.find(r => r.getAttribute('value') === 'Positive');
    expect(positiveRadio).toBeChecked();
  });
});

// ============================================================================
// Toolbar Tests
// ============================================================================

describe('AnnotationInterface - Toolbar', () => {
  const defaultProps = {
    project: createMockProject(),
    task: createMockTask(),
    onAnnotationSave: vi.fn(),
    onAnnotationUpdate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissions.annotation = { canView: true, canCreate: true, canEdit: true, canDelete: false };
  });

  it('renders undo and redo buttons', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByTitle('Undo')).toBeInTheDocument();
    expect(screen.getByTitle('Redo')).toBeInTheDocument();
  });

  it('disables undo button when no history', () => {
    render(<AnnotationInterface {...defaultProps} />);
    const undoButton = screen.getByTitle('Undo');
    expect(undoButton.closest('button')).toBeDisabled();
  });

  it('disables redo button when at end of history', () => {
    render(<AnnotationInterface {...defaultProps} />);
    const redoButton = screen.getByTitle('Redo');
    expect(redoButton.closest('button')).toBeDisabled();
  });

  it('shows history counter', () => {
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText(/History/)).toBeInTheDocument();
  });
});

// ============================================================================
// Validation Tests
// ============================================================================

describe('AnnotationInterface - Validation', () => {
  const defaultProps = {
    project: createMockProject(),
    task: createMockTask(),
    onAnnotationSave: vi.fn(),
    onAnnotationUpdate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissions.annotation = { canView: true, canCreate: true, canEdit: true, canDelete: false };
  });

  it('shows validation error when submitting without sentiment', async () => {
    const user = userEvent.setup();
    render(<AnnotationInterface {...defaultProps} />);

    // Click save without selecting sentiment
    const saveButton = screen.getByRole('button', { name: /Save Annotation/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Please select a sentiment')).toBeInTheDocument();
    });
    expect(defaultProps.onAnnotationSave).not.toHaveBeenCalled();
  });

  it('does not require rating or comment fields', async () => {
    const user = userEvent.setup();
    render(<AnnotationInterface {...defaultProps} />);

    // Select only sentiment (required field)
    const positiveRadio = screen.getByRole('radio', { name: /Positive/i });
    await user.click(positiveRadio);

    const saveButton = screen.getByRole('button', { name: /Save Annotation/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(defaultProps.onAnnotationSave).toHaveBeenCalled();
    });
  });
});

// ============================================================================
// Submission Tests
// ============================================================================

describe('AnnotationInterface - Submission', () => {
  const defaultProps = {
    project: createMockProject(),
    task: createMockTask(),
    onAnnotationSave: vi.fn(),
    onAnnotationUpdate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockPermissions.annotation = { canView: true, canCreate: true, canEdit: true, canDelete: false };
  });

  it('calls onAnnotationSave for new annotation', async () => {
    const user = userEvent.setup();
    render(<AnnotationInterface {...defaultProps} />);

    const positiveRadio = screen.getByRole('radio', { name: /Positive/i });
    await user.click(positiveRadio);

    const saveButton = screen.getByRole('button', { name: /Save Annotation/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(defaultProps.onAnnotationSave).toHaveBeenCalledWith(
        expect.objectContaining({
          task: 100,
          result: expect.arrayContaining([
            expect.objectContaining({
              type: 'choices',
              value: { choices: ['Positive'] },
              from_name: 'sentiment',
              to_name: 'text',
            }),
          ]),
        })
      );
    });
  });

  it('calls onAnnotationUpdate for existing annotation', async () => {
    const user = userEvent.setup();
    const taskWithAnnotation = createMockTask({
      annotations: [createMockAnnotation()],
    });
    render(<AnnotationInterface {...defaultProps} task={taskWithAnnotation} />);

    // Change sentiment to Negative
    const negativeRadio = screen.getByRole('radio', { name: /Negative/i });
    await user.click(negativeRadio);

    const saveButton = screen.getByRole('button', { name: /Save Annotation/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(defaultProps.onAnnotationUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          task: 100,
          result: expect.arrayContaining([
            expect.objectContaining({
              type: 'choices',
              value: { choices: ['Negative'] },
            }),
          ]),
        })
      );
    });
  });

  it('includes comment in submission when provided', async () => {
    const user = userEvent.setup();
    render(<AnnotationInterface {...defaultProps} />);

    const positiveRadio = screen.getByRole('radio', { name: /Positive/i });
    await user.click(positiveRadio);

    const commentInput = screen.getByPlaceholderText('Enter comment...');
    await user.type(commentInput, 'Great quality text');

    const saveButton = screen.getByRole('button', { name: /Save Annotation/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(defaultProps.onAnnotationSave).toHaveBeenCalledWith(
        expect.objectContaining({
          result: expect.arrayContaining([
            expect.objectContaining({
              type: 'textarea',
              value: { text: 'Great quality text' },
            }),
          ]),
        })
      );
    });
  });

  it('quick annotation buttons trigger form submission', async () => {
    const user = userEvent.setup();
    render(<AnnotationInterface {...defaultProps} />);

    // Click the quick "Positive" button
    const quickButtons = screen.getAllByRole('button', { name: /Positive/i });
    // The quick annotation button (not the radio label)
    const quickPositiveBtn = quickButtons.find(
      btn => btn.closest('.ant-btn') !== null && btn.textContent?.includes('Positive')
    );
    if (quickPositiveBtn) {
      await user.click(quickPositiveBtn);
    }

    await waitFor(() => {
      expect(defaultProps.onAnnotationSave).toHaveBeenCalled();
    });
  });
});

// ============================================================================
// Permission Tests
// ============================================================================

describe('AnnotationInterface - Permissions', () => {
  const defaultProps = {
    project: createMockProject(),
    task: createMockTask(),
    onAnnotationSave: vi.fn(),
    onAnnotationUpdate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows read-only tag when user has no create/edit permissions', () => {
    mockPermissions.annotation = { canView: true, canCreate: false, canEdit: false, canDelete: false };
    render(<AnnotationInterface {...defaultProps} />);
    expect(screen.getByText('Read Only')).toBeInTheDocument();
  });

  it('disables save button when user has no permissions', () => {
    mockPermissions.annotation = { canView: true, canCreate: false, canEdit: false, canDelete: false };
    render(<AnnotationInterface {...defaultProps} />);
    const saveButtons = screen.getAllByRole('button', { name: /Save Annotation/i });
    const disabledSave = saveButtons.find(btn => btn.hasAttribute('disabled'));
    expect(disabledSave).toBeDefined();
  });

  it('disables quick annotation buttons when no permissions', () => {
    mockPermissions.annotation = { canView: true, canCreate: false, canEdit: false, canDelete: false };
    render(<AnnotationInterface {...defaultProps} />);

    // Quick annotation buttons should be disabled
    const quickButtons = screen.getAllByRole('button').filter(
      btn => btn.textContent?.includes('Positive') || 
             btn.textContent?.includes('Negative') || 
             btn.textContent?.includes('Neutral')
    );
    quickButtons.forEach(btn => {
      if (btn.closest('.ant-btn')) {
        expect(btn.closest('button')).toBeDisabled();
      }
    });
  });
});
