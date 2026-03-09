/**
 * StateTransitionVisualizer Component Unit Tests
 * 
 * Tests for current state display, button enable/disable logic,
 * timeline rendering, and transition confirmation.
 * 
 * **Validates: Requirements 18.1, 18.2, 18.4**
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import StateTransitionVisualizer, { DataState, StateHistory } from '../StateTransitionVisualizer';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      // Handle nested keys
      if (key.startsWith('stateTransition.')) {
        return key;
      }
      if (key.startsWith('states.')) {
        return key;
      }
      return key;
    },
  }),
}));

describe('StateTransitionVisualizer Component', () => {
  // Sample test data
  const mockStateHistory: StateHistory[] = [
    {
      id: 'history-1',
      state: DataState.RAW,
      timestamp: '2024-01-01T10:00:00Z',
      userId: 'user-1',
    },
    {
      id: 'history-2',
      state: DataState.STRUCTURED,
      timestamp: '2024-01-02T11:00:00Z',
      userId: 'user-2',
      reason: 'Data structured successfully',
    },
    {
      id: 'history-3',
      state: DataState.TEMP_STORED,
      timestamp: '2024-01-03T12:00:00Z',
      userId: 'user-3',
    },
  ];

  const defaultProps = {
    dataId: 'data-123',
    currentState: DataState.TEMP_STORED,
    stateHistory: mockStateHistory,
    onTransition: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Current State Display Tests (Requirement 18.1)
  // ============================================================================

  describe('Current State Display (Requirement 18.1)', () => {
    it('renders the component without crashing', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      expect(screen.getByTestId('state-transition-visualizer')).toBeInTheDocument();
    });

    it('displays the current state tag', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toBeInTheDocument();
    });

    it('displays the correct current state value', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toHaveTextContent('states.temp_stored');
    });

    it('displays current state with blue color tag', () => {
      const { container } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toHaveClass('ant-tag-blue');
    });

    it('displays section title', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByText('stateTransition.title')).toBeInTheDocument();
    });

    it('updates current state when prop changes', () => {
      const { rerender } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toHaveTextContent('states.temp_stored');
      
      rerender(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.UNDER_REVIEW}
        />
      );
      
      expect(currentStateTag).toHaveTextContent('states.under_review');
    });

    it('displays current state for RAW state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.RAW}
          stateHistory={[]}
        />
      );
      
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toHaveTextContent('states.raw');
    });

    it('displays current state for ARCHIVED state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.ARCHIVED}
        />
      );
      
      expect(screen.getByText('states.archived')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Button Enable/Disable Logic Tests (Requirement 18.2)
  // ============================================================================

  describe('Button Enable/Disable Logic (Requirement 18.2)', () => {
    it('displays available transitions section', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByText('stateTransition.availableTransitions')).toBeInTheDocument();
    });

    it('displays transition button for valid next state', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      // TEMP_STORED can transition to UNDER_REVIEW
      const transitionButton = screen.getByTestId('transition-button-under_review');
      expect(transitionButton).toBeInTheDocument();
    });

    it('displays correct number of transition buttons', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      // TEMP_STORED has only 1 valid transition: UNDER_REVIEW
      const transitionButtons = screen.getAllByRole('button').filter(btn =>
        btn.getAttribute('data-testid')?.startsWith('transition-button-')
      );
      expect(transitionButtons.length).toBe(1);
    });

    it('displays multiple transition buttons for states with multiple options', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.UNDER_REVIEW}
        />
      );
      
      // UNDER_REVIEW can transition to REJECTED or APPROVED
      expect(screen.getByTestId('transition-button-rejected')).toBeInTheDocument();
      expect(screen.getByTestId('transition-button-approved')).toBeInTheDocument();
    });

    it('displays no transitions message for terminal states', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.REJECTED}
        />
      );
      
      expect(screen.getByText('stateTransition.noAvailableTransitions')).toBeInTheDocument();
    });

    it('displays no transitions message for ARCHIVED state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.ARCHIVED}
        />
      );
      
      expect(screen.getByText('stateTransition.noAvailableTransitions')).toBeInTheDocument();
    });

    it('calls onTransition when transition button is clicked', () => {
      const onTransition = vi.fn();
      render(<StateTransitionVisualizer {...defaultProps} onTransition={onTransition} />);
      
      const transitionButton = screen.getByTestId('transition-button-under_review');
      fireEvent.click(transitionButton);
      
      expect(onTransition).toHaveBeenCalledWith(DataState.UNDER_REVIEW);
    });

    it('calls onTransition with correct state for multiple options', () => {
      const onTransition = vi.fn();
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.UNDER_REVIEW}
          onTransition={onTransition}
        />
      );
      
      const approveButton = screen.getByTestId('transition-button-approved');
      fireEvent.click(approveButton);
      
      expect(onTransition).toHaveBeenCalledWith(DataState.APPROVED);
      
      const rejectButton = screen.getByTestId('transition-button-rejected');
      fireEvent.click(rejectButton);
      
      expect(onTransition).toHaveBeenCalledWith(DataState.REJECTED);
    });

    it('displays transition buttons with primary type', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      const transitionButton = screen.getByTestId('transition-button-under_review');
      expect(transitionButton).toHaveClass('ant-btn-primary');
    });

    it('displays correct aria-label for transition buttons', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      const transitionButton = screen.getByTestId('transition-button-under_review');
      expect(transitionButton).toHaveAttribute(
        'aria-label',
        'stateTransition.transitionTo states.under_review'
      );
    });

    it('displays transition buttons for RAW state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.RAW}
        />
      );
      
      expect(screen.getByTestId('transition-button-structured')).toBeInTheDocument();
    });

    it('displays transition buttons for IN_SAMPLE_LIBRARY state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.IN_SAMPLE_LIBRARY}
        />
      );
      
      expect(screen.getByTestId('transition-button-annotation_pending')).toBeInTheDocument();
      expect(screen.getByTestId('transition-button-trial_calculation')).toBeInTheDocument();
    });

    it('displays transition buttons for ENHANCED state', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.ENHANCED}
        />
      );
      
      expect(screen.getByTestId('transition-button-in_sample_library')).toBeInTheDocument();
      expect(screen.getByTestId('transition-button-trial_calculation')).toBeInTheDocument();
      expect(screen.getByTestId('transition-button-archived')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Timeline Rendering Tests (Requirement 18.4)
  // ============================================================================

  describe('Timeline Rendering (Requirement 18.4)', () => {
    it('displays state history section', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByText('stateTransition.history')).toBeInTheDocument();
    });

    it('renders timeline component', () => {
      const { container } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const timeline = container.querySelector('.ant-timeline');
      expect(timeline).toBeInTheDocument();
    });

    it('displays all history items', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByTestId('history-item-history-1')).toBeInTheDocument();
      expect(screen.getByTestId('history-item-history-2')).toBeInTheDocument();
      expect(screen.getByTestId('history-item-history-3')).toBeInTheDocument();
    });

    it('displays correct number of timeline items', () => {
      const { container } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const timelineItems = container.querySelectorAll('.ant-timeline-item');
      expect(timelineItems.length).toBe(3);
    });

    it('displays state names in timeline', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      // Use getAllByText since states appear in both current state and history
      const rawStates = screen.getAllByText('states.raw');
      const structuredStates = screen.getAllByText('states.structured');
      const tempStoredStates = screen.getAllByText('states.temp_stored');
      
      expect(rawStates.length).toBeGreaterThan(0);
      expect(structuredStates.length).toBeGreaterThan(0);
      expect(tempStoredStates.length).toBeGreaterThan(0);
    });

    it('displays timestamps in locale format', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('displays reason when provided', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByText(/Data structured successfully/)).toBeInTheDocument();
    });

    it('does not display reason when not provided', () => {
      const { container } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const historyItem1 = screen.getByTestId('history-item-history-1');
      expect(historyItem1.textContent).not.toContain('reason');
    });

    it('displays empty timeline when no history', () => {
      const { container } = render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={[]}
        />
      );
      
      const timeline = container.querySelector('.ant-timeline');
      expect(timeline).toBeInTheDocument();
      
      const timelineItems = container.querySelectorAll('.ant-timeline-item');
      expect(timelineItems.length).toBe(0);
    });

    it('displays single history item correctly', () => {
      const singleHistory: StateHistory[] = [
        {
          id: 'history-1',
          state: DataState.RAW,
          timestamp: '2024-01-01T10:00:00Z',
          userId: 'user-1',
        },
      ];
      
      const { container } = render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={singleHistory}
        />
      );
      
      const timelineItems = container.querySelectorAll('.ant-timeline-item');
      expect(timelineItems.length).toBe(1);
    });

    it('displays long history correctly', () => {
      const longHistory: StateHistory[] = [
        {
          id: 'history-1',
          state: DataState.RAW,
          timestamp: '2024-01-01T10:00:00Z',
          userId: 'user-1',
        },
        {
          id: 'history-2',
          state: DataState.STRUCTURED,
          timestamp: '2024-01-02T11:00:00Z',
          userId: 'user-2',
        },
        {
          id: 'history-3',
          state: DataState.TEMP_STORED,
          timestamp: '2024-01-03T12:00:00Z',
          userId: 'user-3',
        },
        {
          id: 'history-4',
          state: DataState.UNDER_REVIEW,
          timestamp: '2024-01-04T13:00:00Z',
          userId: 'user-4',
        },
        {
          id: 'history-5',
          state: DataState.APPROVED,
          timestamp: '2024-01-05T14:00:00Z',
          userId: 'user-5',
        },
      ];
      
      const { container } = render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={longHistory}
        />
      );
      
      const timelineItems = container.querySelectorAll('.ant-timeline-item');
      expect(timelineItems.length).toBe(5);
    });

    it('displays history items with tags', () => {
      const { container } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      const tags = container.querySelectorAll('.ant-tag');
      // Current state tag + 3 history tags
      expect(tags.length).toBeGreaterThanOrEqual(3);
    });

    it('formats timestamps correctly', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      // Check that timestamps are formatted using toLocaleString
      const historyItem = screen.getByTestId('history-item-history-1');
      expect(historyItem.textContent).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles missing onTransition callback', () => {
      const { container } = render(
        <StateTransitionVisualizer
          {...defaultProps}
          onTransition={() => {}}
        />
      );
      
      const transitionButton = screen.getByTestId('transition-button-under_review');
      
      // Should not throw error
      expect(() => fireEvent.click(transitionButton)).not.toThrow();
    });

    it('handles history with very long reason', () => {
      const historyWithLongReason: StateHistory[] = [
        {
          id: 'history-1',
          state: DataState.RAW,
          timestamp: '2024-01-01T10:00:00Z',
          userId: 'user-1',
          reason: 'This is a very long reason that might break the layout if not handled properly. It contains a lot of text to test how the component handles long content.',
        },
      ];
      
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={historyWithLongReason}
        />
      );
      
      expect(screen.getByText(/very long reason/)).toBeInTheDocument();
    });

    it('handles history with special characters in reason', () => {
      const historyWithSpecialChars: StateHistory[] = [
        {
          id: 'history-1',
          state: DataState.RAW,
          timestamp: '2024-01-01T10:00:00Z',
          userId: 'user-1',
          reason: 'Reason with <special> & "characters"',
        },
      ];
      
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={historyWithSpecialChars}
        />
      );
      
      expect(screen.getByText(/special/)).toBeInTheDocument();
    });

    it('handles invalid timestamp gracefully', () => {
      const historyWithInvalidTimestamp: StateHistory[] = [
        {
          id: 'history-1',
          state: DataState.RAW,
          timestamp: 'invalid-date',
          userId: 'user-1',
        },
      ];
      
      const { container } = render(
        <StateTransitionVisualizer
          {...defaultProps}
          stateHistory={historyWithInvalidTimestamp}
        />
      );
      
      // Should render without crashing
      expect(container.querySelector('.ant-timeline')).toBeInTheDocument();
    });

    it('handles state with no valid transitions', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.REJECTED}
        />
      );
      
      expect(screen.getByText('stateTransition.noAvailableTransitions')).toBeInTheDocument();
      
      const transitionButtons = screen.queryAllByRole('button').filter(btn =>
        btn.getAttribute('data-testid')?.startsWith('transition-button-')
      );
      expect(transitionButtons.length).toBe(0);
    });

    it('handles rapid button clicks', () => {
      const onTransition = vi.fn();
      render(<StateTransitionVisualizer {...defaultProps} onTransition={onTransition} />);
      
      const transitionButton = screen.getByTestId('transition-button-under_review');
      
      fireEvent.click(transitionButton);
      fireEvent.click(transitionButton);
      fireEvent.click(transitionButton);
      
      expect(onTransition).toHaveBeenCalledTimes(3);
    });

    it('handles empty dataId', () => {
      render(
        <StateTransitionVisualizer
          {...defaultProps}
          dataId=""
        />
      );
      
      expect(screen.getByTestId('state-transition-visualizer')).toBeInTheDocument();
    });

    it('handles all possible states', () => {
      const allStates = [
        DataState.RAW,
        DataState.STRUCTURED,
        DataState.TEMP_STORED,
        DataState.UNDER_REVIEW,
        DataState.REJECTED,
        DataState.APPROVED,
        DataState.IN_SAMPLE_LIBRARY,
        DataState.ANNOTATION_PENDING,
        DataState.ANNOTATING,
        DataState.ANNOTATED,
        DataState.ENHANCING,
        DataState.ENHANCED,
        DataState.TRIAL_CALCULATION,
        DataState.ARCHIVED,
      ];
      
      allStates.forEach(state => {
        const { unmount } = render(
          <StateTransitionVisualizer
            {...defaultProps}
            currentState={state}
          />
        );
        
        expect(screen.getByTestId('state-transition-visualizer')).toBeInTheDocument();
        unmount();
      });
    });
  });

  // ============================================================================
  // Integration Tests
  // ============================================================================

  describe('Integration Tests', () => {
    it('displays complete component with all sections', () => {
      render(<StateTransitionVisualizer {...defaultProps} />);
      
      // Current state section
      expect(screen.getByText('stateTransition.title')).toBeInTheDocument();
      expect(screen.getByTestId('current-state-tag')).toBeInTheDocument();
      
      // Available transitions section
      expect(screen.getByText('stateTransition.availableTransitions')).toBeInTheDocument();
      
      // State history section
      expect(screen.getByText('stateTransition.history')).toBeInTheDocument();
    });

    it('updates all sections when state changes', () => {
      const { rerender } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      // Initial state: TEMP_STORED
      const currentStateTag = screen.getByTestId('current-state-tag');
      expect(currentStateTag).toHaveTextContent('states.temp_stored');
      expect(screen.getByTestId('transition-button-under_review')).toBeInTheDocument();
      
      // Change to UNDER_REVIEW
      rerender(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.UNDER_REVIEW}
        />
      );
      
      expect(currentStateTag).toHaveTextContent('states.under_review');
      expect(screen.getByTestId('transition-button-rejected')).toBeInTheDocument();
      expect(screen.getByTestId('transition-button-approved')).toBeInTheDocument();
    });

    it('maintains history when state changes', () => {
      const { rerender } = render(<StateTransitionVisualizer {...defaultProps} />);
      
      expect(screen.getByTestId('history-item-history-1')).toBeInTheDocument();
      
      rerender(
        <StateTransitionVisualizer
          {...defaultProps}
          currentState={DataState.UNDER_REVIEW}
        />
      );
      
      expect(screen.getByTestId('history-item-history-1')).toBeInTheDocument();
    });
  });
});
