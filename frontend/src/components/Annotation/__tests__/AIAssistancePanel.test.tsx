/**
 * AIAssistancePanel Component Tests
 *
 * Tests for the AI Assistance Panel component including:
 * - Rendering with WebSocket connection
 * - Displaying AI suggestions
 * - Handling suggestion accept/reject
 * - Quality alerts display
 * - Real-time updates via WebSocket
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import i18n from '@/locales/config';
import AIAssistancePanel from '../AIAssistancePanel';

// Mock WebSocket hook
const mockWsOn = vi.fn();
const mockWsOff = vi.fn();
const mockWsEmit = vi.fn();

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    on: mockWsOn,
    off: mockWsOff,
    emit: mockWsEmit,
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const mockSuggestions = [
  {
    suggestionId: 'sug_1',
    label: 'Positive',
    confidence: 0.95,
    reasoning: 'Strong positive sentiment indicators',
    similarExamples: 5,
    engineType: 'pre-annotation' as const,
    metadata: {
      patterns: ['excellent', 'great'],
      context: 'Customer review',
    },
  },
  {
    suggestionId: 'sug_2',
    label: 'Negative',
    confidence: 0.75,
    reasoning: 'Moderate negative sentiment',
    similarExamples: 3,
    engineType: 'mid-coverage' as const,
  },
];

const mockQualityAlert = {
  alertId: 'alert_1',
  type: 'warning' as const,
  message: 'Low confidence detected',
  metric: 'confidence',
  threshold: 0.7,
  currentValue: 0.65,
  timestamp: '2026-01-24T10:00:00Z',
};

async function expandQualityAlertsPanel(
  user: ReturnType<typeof userEvent.setup>,
  container: HTMLElement
) {
  await waitFor(() => {
    const header = container.querySelector('.ai-assistance-panel .ant-collapse-header');
    expect(header).toBeTruthy();
  });
  const header = container.querySelector('.ai-assistance-panel .ant-collapse-header') as HTMLElement;
  await user.click(header);
}

describe('AIAssistancePanel', () => {
  const defaultProps = {
    taskId: 1,
    projectId: 100,
    onSuggestionAccept: vi.fn(),
    onSuggestionReject: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ suggestions: [] }),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders AI Assistance Panel with title', () => {
    render(<AIAssistancePanel {...defaultProps} />);
    expect(screen.getByText('AI Assistance')).toBeInTheDocument();
  });

  it('shows disconnected status initially', () => {
    render(<AIAssistancePanel {...defaultProps} />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('establishes WebSocket connection and listens to events', () => {
    render(<AIAssistancePanel {...defaultProps} />);

    // Verify WebSocket event listeners are registered
    expect(mockWsOn).toHaveBeenCalledWith('connect', expect.any(Function));
    expect(mockWsOn).toHaveBeenCalledWith('disconnect', expect.any(Function));
    expect(mockWsOn).toHaveBeenCalledWith('suggestion', expect.any(Function));
    expect(mockWsOn).toHaveBeenCalledWith('quality_alert', expect.any(Function));
    expect(mockWsOn).toHaveBeenCalledWith('suggestion_updated', expect.any(Function));
  });

  it('updates connection status when WebSocket connects', async () => {
    render(<AIAssistancePanel {...defaultProps} />);

    // Simulate WebSocket connect event
    const connectHandler = mockWsOn.mock.calls.find((call) => call[0] === 'connect')?.[1];
    expect(connectHandler).toBeDefined();
    connectHandler?.();

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });
  });

  it('displays AI suggestions when received via WebSocket', async () => {
    render(<AIAssistancePanel {...defaultProps} />);

    // Simulate receiving suggestions via WebSocket
    const suggestionHandler = mockWsOn.mock.calls.find((call) => call[0] === 'suggestion')?.[1];
    expect(suggestionHandler).toBeDefined();
    suggestionHandler?.({ suggestions: mockSuggestions });

    await waitFor(() => {
      expect(screen.getByText('Positive')).toBeInTheDocument();
      expect(screen.getByText('Negative')).toBeInTheDocument();
    });
  });

  it('displays quality alerts when received via WebSocket', async () => {
    const user = userEvent.setup();
    const { container } = render(<AIAssistancePanel {...defaultProps} />);

    // Simulate quality alert via WebSocket
    const alertHandler = mockWsOn.mock.calls.find((call) => call[0] === 'quality_alert')?.[1];
    expect(alertHandler).toBeDefined();
    alertHandler?.(mockQualityAlert);

    await expandQualityAlertsPanel(user, container);

    await waitFor(() => {
      expect(screen.getByText('Low confidence detected')).toBeInTheDocument();
    });
  });

  it('requests suggestions when refresh button is clicked', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ suggestions: mockSuggestions }),
    });

    render(<AIAssistancePanel {...defaultProps} />);

    const refreshButton = screen.getByRole('button', { name: /refresh suggestions/i });
    await user.click(refreshButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/annotation/suggestion',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_id: defaultProps.taskId,
            project_id: defaultProps.projectId,
          }),
        })
      );
    });
  });

  it('handles suggestion acceptance', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    render(<AIAssistancePanel {...defaultProps} />);

    // Add suggestions first
    const suggestionHandler = mockWsOn.mock.calls.find((call) => call[0] === 'suggestion')?.[1];
    suggestionHandler?.({ suggestions: [mockSuggestions[0]] });

    await waitFor(() => {
      expect(screen.getByText('Positive')).toBeInTheDocument();
    });

    // Find and click accept button
    const acceptButton = screen.getByRole('button', { name: /accept/i });
    await user.click(acceptButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/annotation/feedback',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            suggestion_id: 'sug_1',
            accepted: true,
            task_id: defaultProps.taskId,
          }),
        })
      );
      expect(defaultProps.onSuggestionAccept).toHaveBeenCalledWith(mockSuggestions[0]);
    });
  });

  it('handles suggestion rejection with reason', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    render(<AIAssistancePanel {...defaultProps} />);

    // Add suggestions first
    const suggestionHandler = mockWsOn.mock.calls.find((call) => call[0] === 'suggestion')?.[1];
    suggestionHandler?.({ suggestions: [mockSuggestions[0]] });

    await waitFor(() => {
      expect(screen.getByText('Positive')).toBeInTheDocument();
    });

    // Find and click reject button
    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /^confirm$/i }));
  });

  it('shows empty state when no suggestions available', () => {
    render(<AIAssistancePanel {...defaultProps} />);
    expect(screen.getByText('No AI suggestions available')).toBeInTheDocument();
  });

  it('shows loading state when fetching suggestions', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockImplementationOnce(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => ({ suggestions: [] }),
              }),
            100
          )
        )
    );

    const { container } = render(<AIAssistancePanel {...defaultProps} />);

    const refreshButton = screen.getByRole('button', { name: /refresh suggestions/i });
    await user.click(refreshButton);

    await waitFor(() => {
      expect(container.querySelector('.ant-spin-spinning')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    render(<AIAssistancePanel {...defaultProps} />);

    const refreshButton = screen.getByRole('button', { name: /refresh suggestions/i });
    await user.click(refreshButton);

    await waitFor(() => {
      // Error should be logged, component should not crash
      expect(screen.queryByText('Loading AI suggestions...')).not.toBeInTheDocument();
    });
  });

  it('cleans up WebSocket listeners on unmount', () => {
    const { unmount } = render(<AIAssistancePanel {...defaultProps} />);

    unmount();

    expect(mockWsOff).toHaveBeenCalledWith('connect');
    expect(mockWsOff).toHaveBeenCalledWith('disconnect');
    expect(mockWsOff).toHaveBeenCalledWith('suggestion');
    expect(mockWsOff).toHaveBeenCalledWith('quality_alert');
    expect(mockWsOff).toHaveBeenCalledWith('suggestion_updated');
  });

  it('limits quality alerts to 5 most recent', async () => {
    const user = userEvent.setup();
    const { container } = render(<AIAssistancePanel {...defaultProps} />);

    const alertHandler = mockWsOn.mock.calls.find((call) => call[0] === 'quality_alert')?.[1];

    // Add 6 alerts
    for (let i = 0; i < 6; i++) {
      alertHandler?.({
        ...mockQualityAlert,
        alertId: `alert_${i}`,
        message: `Alert ${i}`,
      });
    }

    await expandQualityAlertsPanel(user, container);

    await waitFor(() => {
      expect(screen.queryByText('Alert 0')).not.toBeInTheDocument();
      expect(screen.getByText('Alert 5')).toBeInTheDocument();
    });
  });
});
