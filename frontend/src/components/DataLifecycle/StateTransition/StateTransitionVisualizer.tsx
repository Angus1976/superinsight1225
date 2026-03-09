/**
 * State Transition Visualizer Component
 * 
 * Displays the current state and available transitions for a data item.
 * Shows enabled buttons for valid transitions and disabled buttons for invalid ones.
 * 
 * **Validates: Requirements 18.2, 18.6**
 */

import React from 'react';
import { Button, Timeline, Tag, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import './StateTransitionVisualizer.scss';

// ============================================================================
// Types
// ============================================================================

export enum DataState {
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

export interface StateHistory {
  id: string;
  state: DataState;
  timestamp: string;
  userId: string;
  reason?: string;
}

export interface StateTransitionVisualizerProps {
  dataId: string;
  currentState: DataState;
  stateHistory: StateHistory[];
  onTransition: (targetState: DataState) => void;
}

// ============================================================================
// State Machine Definition
// ============================================================================

const STATE_TRANSITIONS: Record<DataState, DataState[]> = {
  [DataState.RAW]: [DataState.STRUCTURED],
  [DataState.STRUCTURED]: [DataState.TEMP_STORED],
  [DataState.TEMP_STORED]: [DataState.UNDER_REVIEW],
  [DataState.UNDER_REVIEW]: [DataState.REJECTED, DataState.APPROVED],
  [DataState.REJECTED]: [],
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
  [DataState.ARCHIVED]: []
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get valid next states for a given current state
 */
function getValidNextStates(currentState: DataState): DataState[] {
  return STATE_TRANSITIONS[currentState] || [];
}

/**
 * Check if a transition is valid
 */
function isValidTransition(currentState: DataState, targetState: DataState): boolean {
  const validStates = getValidNextStates(currentState);
  return validStates.includes(targetState);
}

// ============================================================================
// Component
// ============================================================================

export const StateTransitionVisualizer: React.FC<StateTransitionVisualizerProps> = ({
  dataId,
  currentState,
  stateHistory,
  onTransition
}) => {
  const { t } = useTranslation('dataLifecycle');

  const validNextStates = getValidNextStates(currentState);

  return (
    <div className="state-transition-visualizer" data-testid="state-transition-visualizer">
      {/* Current State */}
      <div className="current-state-section">
        <h3>{t('stateTransition.title')}</h3>
        <div className="current-state">
          <Tag color="blue" data-testid="current-state-tag">
            {t(`states.${currentState}`)}
          </Tag>
        </div>
      </div>

      {/* Available Transitions */}
      <div className="available-transitions-section">
        <h4>{t('stateTransition.availableTransitions')}</h4>
        {validNextStates.length > 0 ? (
          <Space wrap>
            {validNextStates.map(state => (
              <Button
                key={state}
                type="primary"
                onClick={() => onTransition(state)}
                data-testid={`transition-button-${state}`}
                aria-label={`${t('stateTransition.transitionTo')} ${t(`states.${state}`)}`}
              >
                {t('stateTransition.transitionTo')} {t(`states.${state}`)}
              </Button>
            ))}
          </Space>
        ) : (
          <p className="no-transitions">{t('stateTransition.noAvailableTransitions')}</p>
        )}
      </div>

      {/* State History */}
      <div className="state-history-section">
        <h4>{t('stateTransition.history')}</h4>
        <Timeline>
          {stateHistory.map(history => (
            <Timeline.Item key={history.id} data-testid={`history-item-${history.id}`}>
              <div className="history-item">
                <Tag>{t(`states.${history.state}`)}</Tag>
                <span className="timestamp">{new Date(history.timestamp).toLocaleString()}</span>
                {history.reason && <span className="reason">- {history.reason}</span>}
              </div>
            </Timeline.Item>
          ))}
        </Timeline>
      </div>
    </div>
  );
};

export default StateTransitionVisualizer;
