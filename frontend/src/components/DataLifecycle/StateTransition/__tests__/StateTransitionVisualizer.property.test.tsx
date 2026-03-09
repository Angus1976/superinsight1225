/**
 * State Transition Visualizer Property-Based Tests
 * 
 * **Property 28: State Transition Button Validity**
 * **Validates: Requirements 18.2, 18.6**
 * 
 * Property-based tests to verify that the StateTransitionVisualizer component
 * correctly enables/disables transition buttons based on the state machine rules.
 * 
 * **Feature: data-lifecycle-management**
 * **Testing Framework: fast-check**
 * **Minimum Iterations: 100 per property**
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { StateTransitionVisualizer } from '../StateTransitionVisualizer';

// ============================================================================
// State Machine Definition (matches backend)
// ============================================================================

enum DataState {
  RAW = 'raw',
  STRUCTURED = 'structured',
  TEMP_STORED = 'temp_stored',
  UNDER_REVIEW = 'under_review',
  REJECTED = 'rejected',
  APPROVED = 'approved',
  IN_SAMPLE_LIBRARY = 'in_sample_library',
  ANNOTATION_PENDING = 'annotation_pending',
  ANNOTATING = 'annotating',
  ANNOTATED = 'annotated',
  ENHANCING = 'enhancing',
  ENHANCED = 'enhanced',
  TRIAL_CALCULATION = 'trial_calculation',
  ARCHIVED = 'archived'
}

// Valid state transitions mapping: current_state -> set of valid next states
const STATE_TRANSITIONS: Record<DataState, DataState[]> = {
  [DataState.RAW]: [DataState.STRUCTURED],
  [DataState.STRUCTURED]: [DataState.TEMP_STORED],
  [DataState.TEMP_STORED]: [DataState.UNDER_REVIEW],
  [DataState.UNDER_REVIEW]: [DataState.REJECTED, DataState.APPROVED],
  [DataState.REJECTED]: [], // Terminal state
  [DataState.APPROVED]: [DataState.IN_SAMPLE_LIBRARY],
  [DataState.IN_SAMPLE_LIBRARY]: [
    DataState.ANNOTATION_PENDING,
    DataState.TRIAL_CALCULATION
  ],
  [DataState.ANNOTATION_PENDING]: [DataState.ANNOTATING],
  [DataState.ANNOTATING]: [DataState.ANNOTATED],
  [DataState.ANNOTATED]: [
    DataState.ENHANCING,
    DataState.TRIAL_CALCULATION
  ],
  [DataState.ENHANCING]: [DataState.ENHANCED],
  [DataState.ENHANCED]: [
    DataState.IN_SAMPLE_LIBRARY,
    DataState.TRIAL_CALCULATION,
    DataState.ARCHIVED
  ],
  [DataState.TRIAL_CALCULATION]: [
    DataState.IN_SAMPLE_LIBRARY,
    DataState.ANNOTATED,
    DataState.ENHANCED
  ],
  [DataState.ARCHIVED]: [] // Terminal state
};

// ============================================================================
// Test Generators
// ============================================================================

/**
 * Generate arbitrary data state
 */
const arbitraryDataState = (): fc.Arbitrary<DataState> =>
  fc.constantFrom(...Object.values(DataState));

/**
 * Generate arbitrary data ID
 */
const arbitraryDataId = (): fc.Arbitrary<string> =>
  fc.uuid();

/**
 * Generate arbitrary state history
 */
const arbitraryStateHistory = (currentState: DataState): fc.Arbitrary<Array<{
  id: string;
  state: DataState;
  timestamp: string;
  userId: string;
}>> =>
  fc.array(
    fc.record({
      id: fc.uuid(),
      state: fc.constantFrom(...Object.values(DataState)),
      timestamp: fc.date().map(d => d.toISOString()),
      userId: fc.uuid()
    }),
    { minLength: 1, maxLength: 10 }
  ).map(history => [
    ...history,
    {
      id: fc.sample(fc.uuid(), 1)[0],
      state: currentState,
      timestamp: new Date().toISOString(),
      userId: fc.sample(fc.uuid(), 1)[0]
    }
  ]);

// ============================================================================
// Mock Setup
// ============================================================================

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: 'en',
      changeLanguage: vi.fn()
    }
  })
}));

// ============================================================================
// Property Tests
// ============================================================================

describe('StateTransitionVisualizer Property-Based Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Property 28: State Transition Button Validity
   * 
   * For any given state, only valid next states should have enabled buttons,
   * and invalid transitions should have disabled buttons.
   * 
   * **Validates: Requirements 18.2, 18.6**
   */
  it('Property 28: should only enable buttons for valid state transitions', () => {
    fc.assert(
      fc.property(
        arbitraryDataState(),
        arbitraryDataId(),
        (currentState, dataId) => {
          // Arrange
          const validNextStates = STATE_TRANSITIONS[currentState];
          const allStates = Object.values(DataState);
          const invalidNextStates = allStates.filter(
            state => !validNextStates.includes(state) && state !== currentState
          );

          const mockOnTransition = vi.fn();
          const mockStateHistory = [
            {
              id: '123',
              state: currentState,
              timestamp: new Date().toISOString(),
              userId: 'user-123'
            }
          ];

          // Act
          const { container } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={currentState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          // Assert: Valid transitions should have enabled buttons
          validNextStates.forEach(validState => {
            const button = container.querySelector(
              `[data-testid="transition-button-${validState}"]`
            );
            
            if (button) {
              // Button should exist and not be disabled
              expect(button).toBeTruthy();
              expect(button.hasAttribute('disabled')).toBe(false);
              expect(button.getAttribute('aria-disabled')).not.toBe('true');
            }
          });

          // Assert: Invalid transitions should have disabled buttons or not exist
          invalidNextStates.forEach(invalidState => {
            const button = container.querySelector(
              `[data-testid="transition-button-${invalidState}"]`
            );
            
            if (button) {
              // If button exists, it must be disabled
              const isDisabled = 
                button.hasAttribute('disabled') || 
                button.getAttribute('aria-disabled') === 'true' ||
                button.classList.contains('ant-btn-disabled');
              
              expect(isDisabled).toBe(true);
            }
            // If button doesn't exist, that's also valid (not showing invalid transitions)
          });

          // Assert: Current state button should not be present or should be disabled
          const currentStateButton = container.querySelector(
            `[data-testid="transition-button-${currentState}"]`
          );
          
          if (currentStateButton) {
            const isDisabled = 
              currentStateButton.hasAttribute('disabled') || 
              currentStateButton.getAttribute('aria-disabled') === 'true' ||
              currentStateButton.classList.contains('ant-btn-disabled');
            
            expect(isDisabled).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 28.1: Terminal States Have No Enabled Buttons
   * 
   * Terminal states (REJECTED, ARCHIVED) should have no enabled transition buttons.
   * 
   * **Validates: Requirements 18.2, 18.6**
   */
  it('Property 28.1: terminal states should have no enabled transition buttons', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(DataState.REJECTED, DataState.ARCHIVED),
        arbitraryDataId(),
        (terminalState, dataId) => {
          // Arrange
          const mockOnTransition = vi.fn();
          const mockStateHistory = [
            {
              id: '123',
              state: terminalState,
              timestamp: new Date().toISOString(),
              userId: 'user-123'
            }
          ];

          // Act
          const { container } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={terminalState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          // Assert: No enabled buttons should exist
          const allButtons = container.querySelectorAll('[data-testid^="transition-button-"]');
          
          allButtons.forEach(button => {
            const isDisabled = 
              button.hasAttribute('disabled') || 
              button.getAttribute('aria-disabled') === 'true' ||
              button.classList.contains('ant-btn-disabled');
            
            expect(isDisabled).toBe(true);
          });
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Property 28.2: Button Count Matches Valid Transitions
   * 
   * The number of enabled buttons should match the number of valid next states.
   * 
   * **Validates: Requirements 18.2**
   */
  it('Property 28.2: number of enabled buttons should match valid next states count', () => {
    fc.assert(
      fc.property(
        arbitraryDataState(),
        arbitraryDataId(),
        (currentState, dataId) => {
          // Arrange
          const validNextStates = STATE_TRANSITIONS[currentState];
          const mockOnTransition = vi.fn();
          const mockStateHistory = [
            {
              id: '123',
              state: currentState,
              timestamp: new Date().toISOString(),
              userId: 'user-123'
            }
          ];

          // Act
          const { container } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={currentState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          // Assert: Count enabled buttons
          const allButtons = container.querySelectorAll('[data-testid^="transition-button-"]');
          let enabledCount = 0;

          allButtons.forEach(button => {
            const isDisabled = 
              button.hasAttribute('disabled') || 
              button.getAttribute('aria-disabled') === 'true' ||
              button.classList.contains('ant-btn-disabled');
            
            if (!isDisabled) {
              enabledCount++;
            }
          });

          // The number of enabled buttons should equal the number of valid next states
          expect(enabledCount).toBe(validNextStates.length);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 28.3: Button Labels Match State Names
   * 
   * Each transition button should have a label that corresponds to the target state.
   * 
   * **Validates: Requirements 18.2**
   */
  it('Property 28.3: transition buttons should have labels matching target states', () => {
    fc.assert(
      fc.property(
        arbitraryDataState(),
        arbitraryDataId(),
        (currentState, dataId) => {
          // Arrange
          const validNextStates = STATE_TRANSITIONS[currentState];
          const mockOnTransition = vi.fn();
          const mockStateHistory = [
            {
              id: '123',
              state: currentState,
              timestamp: new Date().toISOString(),
              userId: 'user-123'
            }
          ];

          // Act
          const { container } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={currentState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          // Assert: Each valid next state should have a button with correct label
          validNextStates.forEach(validState => {
            const button = container.querySelector(
              `[data-testid="transition-button-${validState}"]`
            );
            
            if (button) {
              // Button should contain the state name in its text or aria-label
              const buttonText = button.textContent || '';
              const ariaLabel = button.getAttribute('aria-label') || '';
              
              // The button should reference the target state somehow
              const containsStateReference = 
                buttonText.includes(validState) ||
                ariaLabel.includes(validState) ||
                buttonText.includes(`states.${validState}`) || // i18n key
                ariaLabel.includes(`states.${validState}`);
              
              expect(containsStateReference).toBe(true);
            }
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 28.4: State Consistency Across Renders
   * 
   * Re-rendering with the same state should produce the same button enabled/disabled pattern.
   * 
   * **Validates: Requirements 18.2, 18.6**
   */
  it('Property 28.4: button states should be consistent across re-renders', () => {
    fc.assert(
      fc.property(
        arbitraryDataState(),
        arbitraryDataId(),
        (currentState, dataId) => {
          // Arrange
          const mockOnTransition = vi.fn();
          const mockStateHistory = [
            {
              id: '123',
              state: currentState,
              timestamp: new Date().toISOString(),
              userId: 'user-123'
            }
          ];

          // Act: First render
          const { container: container1, unmount } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={currentState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          const buttons1 = Array.from(
            container1.querySelectorAll('[data-testid^="transition-button-"]')
          );
          const buttonStates1 = buttons1.map(button => ({
            testId: button.getAttribute('data-testid'),
            disabled: 
              button.hasAttribute('disabled') || 
              button.getAttribute('aria-disabled') === 'true' ||
              button.classList.contains('ant-btn-disabled')
          }));

          unmount();

          // Act: Second render
          const { container: container2 } = render(
            <StateTransitionVisualizer
              dataId={dataId}
              currentState={currentState}
              stateHistory={mockStateHistory}
              onTransition={mockOnTransition}
            />
          );

          const buttons2 = Array.from(
            container2.querySelectorAll('[data-testid^="transition-button-"]')
          );
          const buttonStates2 = buttons2.map(button => ({
            testId: button.getAttribute('data-testid'),
            disabled: 
              button.hasAttribute('disabled') || 
              button.getAttribute('aria-disabled') === 'true' ||
              button.classList.contains('ant-btn-disabled')
          }));

          // Assert: Button states should be identical
          expect(buttonStates1).toEqual(buttonStates2);
        }
      ),
      { numRuns: 100 }
    );
  });
});
