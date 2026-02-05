/**
 * SuggestionCard Component Tests
 *
 * Tests for the AI Suggestion Card component including:
 * - Rendering suggestion details
 * - Confidence visualization
 * - Accept/Reject actions
 * - Rejection reason modal
 * - Engine type badges
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import SuggestionCard from '../SuggestionCard';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        'annotation:labels.confidence': 'Confidence',
        'annotation:labels.details': 'Details',
        'annotation:labels.reasoning': 'Reasoning',
        'annotation:labels.patterns': 'Patterns',
        'annotation:labels.context': 'Context',
        'annotation:actions.accept': 'Accept',
        'annotation:actions.reject': 'Reject',
        'annotation:modals.reject_suggestion': 'Reject Suggestion',
        'annotation:placeholders.reject_reason': 'Optional: Enter reason for rejection...',
        'annotation:messages.reject_reason_prompt':
          'Optionally provide a reason for rejecting this suggestion',
        'annotation:tooltips.similar_examples': `${options?.count || 0} similar examples found`,
        'ai_annotation:engine_types.pre_annotation': 'Pre-annotation',
        'ai_annotation:engine_types.mid_coverage': 'Mid-coverage',
        'ai_annotation:engine_types.post_validation': 'Post-validation',
        'common:actions.confirm': 'Confirm',
        'common:actions.cancel': 'Cancel',
      };
      return translations[key] || key;
    },
  }),
}));

const mockSuggestion = {
  suggestionId: 'sug_123',
  label: 'Positive Sentiment',
  confidence: 0.92,
  reasoning: 'Contains positive keywords and sentiment markers',
  similarExamples: 8,
  engineType: 'pre-annotation' as const,
  metadata: {
    patterns: ['excellent', 'great', 'wonderful'],
    context: 'Product review context',
  },
};

describe('SuggestionCard', () => {
  const mockOnAccept = vi.fn();
  const mockOnReject = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders suggestion label', () => {
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText('Positive Sentiment')).toBeInTheDocument();
  });

  it('displays confidence score as percentage', () => {
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText(/92\.0%/)).toBeInTheDocument();
  });

  it('shows engine type badge', () => {
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText('Pre-annotation')).toBeInTheDocument();
  });

  it('displays similar examples count', () => {
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('shows reasoning when expanded', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    // Find and click the details collapse
    const detailsButton = screen.getByText('Details');
    await user.click(detailsButton);

    await waitFor(() => {
      expect(
        screen.getByText('Contains positive keywords and sentiment markers')
      ).toBeInTheDocument();
    });
  });

  it('displays pattern tags when expanded', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const detailsButton = screen.getByText('Details');
    await user.click(detailsButton);

    await waitFor(() => {
      expect(screen.getByText('excellent')).toBeInTheDocument();
      expect(screen.getByText('great')).toBeInTheDocument();
      expect(screen.getByText('wonderful')).toBeInTheDocument();
    });
  });

  it('shows context information when expanded', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const detailsButton = screen.getByText('Details');
    await user.click(detailsButton);

    await waitFor(() => {
      expect(screen.getByText('Product review context')).toBeInTheDocument();
    });
  });

  it('calls onAccept when Accept button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const acceptButton = screen.getByRole('button', { name: /accept/i });
    await user.click(acceptButton);

    expect(mockOnAccept).toHaveBeenCalledTimes(1);
  });

  it('opens rejection modal when Reject button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    await waitFor(() => {
      expect(screen.getByText('Reject Suggestion')).toBeInTheDocument();
      expect(
        screen.getByText('Optionally provide a reason for rejecting this suggestion')
      ).toBeInTheDocument();
    });
  });

  it('calls onReject with reason when rejection is confirmed', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    // Open reject modal
    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    // Enter rejection reason
    const textArea = screen.getByPlaceholderText(/enter reason for rejection/i);
    await user.type(textArea, 'Incorrect sentiment classification');

    // Confirm rejection
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockOnReject).toHaveBeenCalledWith('Incorrect sentiment classification');
    });
  });

  it('calls onReject without reason when rejection is confirmed without text', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockOnReject).toHaveBeenCalledWith(undefined);
    });
  });

  it('closes rejection modal when Cancel is clicked', async () => {
    const user = userEvent.setup();
    render(
      <SuggestionCard
        suggestion={mockSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText('Reject Suggestion')).not.toBeInTheDocument();
    });
    expect(mockOnReject).not.toHaveBeenCalled();
  });

  it('uses green color for high confidence (>= 0.9)', () => {
    const highConfidenceSuggestion = { ...mockSuggestion, confidence: 0.95 };
    const { container } = render(
      <SuggestionCard
        suggestion={highConfidenceSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    // Check for green border color
    const card = container.querySelector('.suggestion-card');
    expect(card).toHaveStyle({ borderLeft: expect.stringContaining('#52c41a') });
  });

  it('uses blue color for medium confidence (0.7-0.9)', () => {
    const mediumConfidenceSuggestion = { ...mockSuggestion, confidence: 0.8 };
    const { container } = render(
      <SuggestionCard
        suggestion={mediumConfidenceSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const card = container.querySelector('.suggestion-card');
    expect(card).toHaveStyle({ borderLeft: expect.stringContaining('#1890ff') });
  });

  it('uses orange color for low confidence (0.5-0.7)', () => {
    const lowConfidenceSuggestion = { ...mockSuggestion, confidence: 0.6 };
    const { container } = render(
      <SuggestionCard
        suggestion={lowConfidenceSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const card = container.querySelector('.suggestion-card');
    expect(card).toHaveStyle({ borderLeft: expect.stringContaining('#faad14') });
  });

  it('uses red color for very low confidence (< 0.5)', () => {
    const veryLowConfidenceSuggestion = { ...mockSuggestion, confidence: 0.4 };
    const { container } = render(
      <SuggestionCard
        suggestion={veryLowConfidenceSuggestion}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const card = container.querySelector('.suggestion-card');
    expect(card).toHaveStyle({ borderLeft: expect.stringContaining('#ff4d4f') });
  });

  it('handles suggestion without metadata gracefully', () => {
    const suggestionWithoutMetadata = {
      ...mockSuggestion,
      reasoning: undefined,
      metadata: undefined,
    };

    render(
      <SuggestionCard
        suggestion={suggestionWithoutMetadata}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    // Should still render basic info
    expect(screen.getByText('Positive Sentiment')).toBeInTheDocument();
    expect(screen.getByText(/92\.0%/)).toBeInTheDocument();
  });

  it('handles suggestion with empty patterns array', async () => {
    const user = userEvent.setup();
    const suggestionWithEmptyPatterns = {
      ...mockSuggestion,
      metadata: { patterns: [], context: 'Some context' },
    };

    render(
      <SuggestionCard
        suggestion={suggestionWithEmptyPatterns}
        onAccept={mockOnAccept}
        onReject={mockOnReject}
      />
    );

    const detailsButton = screen.getByText('Details');
    await user.click(detailsButton);

    await waitFor(() => {
      // Should show context but not patterns section
      expect(screen.getByText('Some context')).toBeInTheDocument();
      expect(screen.queryByText('Patterns')).not.toBeInTheDocument();
    });
  });
});
