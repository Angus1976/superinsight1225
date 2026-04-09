/**
 * AITrialDashboard Component Unit Tests
 * 
 * Tests for trial table rendering, multi-select for comparison,
 * execute and view results actions, and comparison modal.
 * 
 * Requirements: 16.3, 16.4, 16.5
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import AITrialDashboard from '../AITrialDashboard';
import type { AITrialDashboardProps } from '../AITrialDashboard';
import type { AITrial } from '@/types/dataLifecycle';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === 'common.pagination.total' && params) {
        return `Total ${params.total} items`;
      }
      return key;
    },
  }),
}));

describe('AITrialDashboard Component', () => {
  // Sample test data
  const mockTrials: AITrial[] = [
    {
      id: 'trial-1',
      name: 'Grammar Check Trial',
      dataStage: 'sample_library',
      aiModel: 'GPT-4',
      status: 'created',
      config: {},
      createdBy: 'user-1',
      createdAt: '2024-01-01T10:00:00Z',
    },
    {
      id: 'trial-2',
      name: 'Style Analysis Trial',
      dataStage: 'annotated',
      aiModel: 'Claude-3',
      status: 'running',
      config: {},
      createdBy: 'user-1',
      createdAt: '2024-01-02T10:00:00Z',
    },
    {
      id: 'trial-3',
      name: 'Content Enhancement Trial',
      dataStage: 'enhanced',
      aiModel: 'GPT-4',
      status: 'completed',
      config: {},
      results: { accuracy: 0.95 },
      createdBy: 'user-1',
      createdAt: '2024-01-03T10:00:00Z',
      completedAt: '2024-01-03T12:00:00Z',
    },
    {
      id: 'trial-4',
      name: 'Translation Trial',
      dataStage: 'data_source',
      aiModel: 'Claude-3',
      status: 'completed',
      config: {},
      results: { accuracy: 0.92 },
      createdBy: 'user-2',
      createdAt: '2024-01-04T10:00:00Z',
      completedAt: '2024-01-04T11:30:00Z',
    },
    {
      id: 'trial-5',
      name: 'Failed Trial',
      dataStage: 'temp_table',
      aiModel: 'GPT-4',
      status: 'failed',
      config: {},
      createdBy: 'user-1',
      createdAt: '2024-01-05T10:00:00Z',
    },
  ];

  const defaultProps: AITrialDashboardProps = {
    trials: mockTrials,
    loading: false,
    pagination: {
      page: 1,
      pageSize: 10,
      total: 5,
    },
    onCreateTrial: vi.fn(),
    onExecute: vi.fn(),
    onViewResults: vi.fn(),
    onCompare: vi.fn(),
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Trial Table Rendering Tests (Requirement 16.3, 16.4, 16.5)
  // ============================================================================

  describe('Trial Table Rendering', () => {
    it('renders the component without crashing', () => {
      render(<AITrialDashboard {...defaultProps} />);
      expect(screen.getByText('Grammar Check Trial')).toBeInTheDocument();
    });

    it('renders all trial rows', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('Grammar Check Trial')).toBeInTheDocument();
      expect(screen.getByText('Style Analysis Trial')).toBeInTheDocument();
      expect(screen.getByText('Content Enhancement Trial')).toBeInTheDocument();
      expect(screen.getByText('Translation Trial')).toBeInTheDocument();
      expect(screen.getByText('Failed Trial')).toBeInTheDocument();
    });

    it('displays correct column headers', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getAllByText('aiTrial.columns.name')[0]).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.columns.dataStage')[0]).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.columns.aiModel')[0]).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.columns.status')[0]).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.columns.createdAt')[0]).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.columns.actions')[0]).toBeInTheDocument();
    });

    it('displays loading state correctly', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} loading={true} />);
      
      const loadingSpinner = container.querySelector('.ant-spin');
      expect(loadingSpinner).toBeInTheDocument();
    });

    it('displays empty state when no trials', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} trials={[]} />);
      
      const emptyState = container.querySelector('.ant-empty');
      expect(emptyState).toBeInTheDocument();
    });

    it('displays trial names correctly', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('Grammar Check Trial')).toBeInTheDocument();
      expect(screen.getByText('Style Analysis Trial')).toBeInTheDocument();
      expect(screen.getByText('Content Enhancement Trial')).toBeInTheDocument();
    });

    it('displays AI models correctly', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const gpt4Elements = screen.getAllByText('GPT-4');
      const claude3Elements = screen.getAllByText('Claude-3');
      
      expect(gpt4Elements.length).toBeGreaterThan(0);
      expect(claude3Elements.length).toBeGreaterThan(0);
    });

    it('displays data stages with translation keys', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.dataStages.sample_library')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.dataStages.annotated')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.dataStages.enhanced')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.dataStages.data_source')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.dataStages.temp_table')).toBeInTheDocument();
    });

    it('displays trial statuses as tags', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.status.created')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.status.running')).toBeInTheDocument();
      expect(screen.getAllByText('aiTrial.status.completed').length).toBe(2);
      expect(screen.getByText('aiTrial.status.failed')).toBeInTheDocument();
    });

    it('displays created dates in locale format', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('displays statistics cards', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.statistics.totalTrials')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.statistics.completedTrials')).toBeInTheDocument();
      expect(screen.getByText('aiTrial.statistics.runningTrials')).toBeInTheDocument();
    });

    it('calculates total trials correctly', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('calculates completed trials correctly', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('calculates running trials correctly', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      // Find the running trials statistic card specifically
      const runningTrialsCard = Array.from(container.querySelectorAll('.ant-statistic-title'))
        .find(el => el.textContent === 'aiTrial.statistics.runningTrials');
      
      const runningTrialsValue = runningTrialsCard?.closest('.ant-statistic')
        ?.querySelector('.ant-statistic-content-value-int');
      
      expect(runningTrialsValue?.textContent).toBe('1');
    });
  });

  // ============================================================================
  // Multi-Select for Comparison Tests (Requirement 16.5)
  // ============================================================================

  describe('Multi-Select for Comparison (Requirement 16.5)', () => {
    it('displays row selection checkboxes', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it('enables checkboxes only for completed trials', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      // trial-3 and trial-4 are completed, should be enabled
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const completedCheckbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const completedCheckbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      expect(completedCheckbox1).not.toBeDisabled();
      expect(completedCheckbox2).not.toBeDisabled();
    });

    it('disables checkboxes for non-completed trials', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      // trial-1 is created, should be disabled
      const createdRow = Array.from(rows).find(row => 
        row.textContent?.includes('Grammar Check Trial')
      );
      
      const createdCheckbox = createdRow?.querySelector('input[type="checkbox"]');
      expect(createdCheckbox).toBeDisabled();
    });

    it('allows selecting multiple completed trials', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        expect(checkbox1).toBeChecked();
        expect(checkbox2).toBeChecked();
      }
    });

    it('displays compare button', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.compare')).toBeInTheDocument();
    });

    it('disables compare button when less than 2 trials selected', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const compareButton = screen.getByText('aiTrial.compare').closest('button');
      expect(compareButton).toBeDisabled();
    });

    it('enables compare button when 2 or more trials selected', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        expect(compareButton).not.toBeDisabled();
      }
    });

    it('calls onCompare with selected trial IDs when compare button clicked', () => {
      const onCompare = vi.fn();
      const { container } = render(<AITrialDashboard {...defaultProps} onCompare={onCompare} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          expect(onCompare).toHaveBeenCalledWith(['trial-3', 'trial-4']);
        }
      }
    });

    it('displays compare icon in compare button', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const compareIcon = container.querySelector('[aria-label="swap"]');
      expect(compareIcon).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Execute Action Tests (Requirement 16.3)
  // ============================================================================

  describe('Execute Action (Requirement 16.3)', () => {
    it('displays execute button for created trials', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.actions.execute')).toBeInTheDocument();
    });

    it('does not display execute button for running trials', () => {
      const runningTrials: AITrial[] = [
        {
          id: 'trial-running',
          name: 'Running Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'running',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={runningTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.execute')).not.toBeInTheDocument();
    });

    it('does not display execute button for completed trials', () => {
      const completedTrials: AITrial[] = [
        {
          id: 'trial-completed',
          name: 'Completed Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'completed',
          config: {},
          results: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
          completedAt: '2024-01-01T12:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={completedTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.execute')).not.toBeInTheDocument();
    });

    it('does not display execute button for failed trials', () => {
      const failedTrials: AITrial[] = [
        {
          id: 'trial-failed',
          name: 'Failed Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'failed',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={failedTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.execute')).not.toBeInTheDocument();
    });

    it('calls onExecute with trial ID when execute button clicked', () => {
      const onExecute = vi.fn();
      render(<AITrialDashboard {...defaultProps} onExecute={onExecute} />);
      
      const executeButton = screen.getByText('aiTrial.actions.execute');
      fireEvent.click(executeButton);
      
      expect(onExecute).toHaveBeenCalledWith('trial-1');
    });

    it('displays execute icon in execute button', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const executeIcon = container.querySelector('.anticon-play-circle');
      expect(executeIcon).toBeInTheDocument();
    });

    it('execute button is styled as text button', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const executeButton = screen.getByText('aiTrial.actions.execute').closest('button');
      expect(executeButton).toHaveClass('ant-btn-text');
    });

    it('displays execute button only for trials with created status', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const executeButtons = screen.getAllByText('aiTrial.actions.execute');
      expect(executeButtons.length).toBe(1);
    });
  });

  // ============================================================================
  // View Results Action Tests (Requirement 16.4)
  // ============================================================================

  describe('View Results Action (Requirement 16.4)', () => {
    it('displays view results button for completed trials', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const viewResultsButtons = screen.getAllByText('aiTrial.actions.viewResults');
      expect(viewResultsButtons.length).toBe(2);
    });

    it('does not display view results button for created trials', () => {
      const createdTrials: AITrial[] = [
        {
          id: 'trial-created',
          name: 'Created Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'created',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={createdTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.viewResults')).not.toBeInTheDocument();
    });

    it('does not display view results button for running trials', () => {
      const runningTrials: AITrial[] = [
        {
          id: 'trial-running',
          name: 'Running Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'running',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={runningTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.viewResults')).not.toBeInTheDocument();
    });

    it('does not display view results button for failed trials', () => {
      const failedTrials: AITrial[] = [
        {
          id: 'trial-failed',
          name: 'Failed Trial',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'failed',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={failedTrials} />);
      
      expect(screen.queryByText('aiTrial.actions.viewResults')).not.toBeInTheDocument();
    });

    it('calls onViewResults with trial ID when view results button clicked', () => {
      const onViewResults = vi.fn();
      render(<AITrialDashboard {...defaultProps} onViewResults={onViewResults} />);
      
      const viewResultsButtons = screen.getAllByText('aiTrial.actions.viewResults');
      fireEvent.click(viewResultsButtons[0]);
      
      expect(onViewResults).toHaveBeenCalledWith('trial-3');
    });

    it('displays view results icon in view results button', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const viewResultsIcon = container.querySelector('[aria-label="bar-chart"]');
      expect(viewResultsIcon).toBeInTheDocument();
    });

    it('view results button is styled as text button', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const viewResultsButton = screen.getAllByText('aiTrial.actions.viewResults')[0].closest('button');
      expect(viewResultsButton).toHaveClass('ant-btn-text');
    });

    it('displays view results button for all completed trials', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const viewResultsButtons = screen.getAllByText('aiTrial.actions.viewResults');
      expect(viewResultsButtons.length).toBe(2);
    });

    it('calls onViewResults with correct trial ID for each completed trial', () => {
      const onViewResults = vi.fn();
      render(<AITrialDashboard {...defaultProps} onViewResults={onViewResults} />);
      
      const viewResultsButtons = screen.getAllByText('aiTrial.actions.viewResults');
      
      fireEvent.click(viewResultsButtons[0]);
      expect(onViewResults).toHaveBeenCalledWith('trial-3');
      
      fireEvent.click(viewResultsButtons[1]);
      expect(onViewResults).toHaveBeenCalledWith('trial-4');
    });
  });

  // ============================================================================
  // Comparison Modal Tests (Requirement 16.5)
  // ============================================================================

  describe('Comparison Modal (Requirement 16.5)', () => {
    it('does not display comparison modal initially', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.queryByText('aiTrial.comparisonModal.title')).not.toBeInTheDocument();
    });

    it('opens comparison modal when compare button clicked with 2+ trials selected', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            expect(screen.getByText('aiTrial.comparisonModal.title')).toBeInTheDocument();
          });
        }
      }
    });

    it('displays comparison modal description', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            expect(screen.getByText('aiTrial.comparisonModal.description')).toBeInTheDocument();
          });
        }
      }
    });

    it('displays selected trials in comparison modal', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            const modal = screen.getByText('aiTrial.comparisonModal.title').closest('.ant-modal');
            expect(modal).toBeInTheDocument();
            
            // Check that trial names are displayed in modal
            const modalContent = modal?.querySelector('.ant-modal-body');
            expect(modalContent?.textContent).toContain('Content Enhancement Trial');
            expect(modalContent?.textContent).toContain('Translation Trial');
          });
        }
      }
    });

    it('displays trial details in comparison modal', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            const modal = screen.getByText('aiTrial.comparisonModal.title').closest('.ant-modal');
            const modalContent = modal?.querySelector('.ant-modal-body');
            
            // Check that AI models are displayed
            expect(modalContent?.textContent).toContain('GPT-4');
            expect(modalContent?.textContent).toContain('Claude-3');
          });
        }
      }
    });

    it('closes comparison modal when close button clicked', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            expect(screen.getByText('aiTrial.comparisonModal.title')).toBeInTheDocument();
          });
          
          const closeButton = screen.getByText('common.actions.close');
          fireEvent.click(closeButton);
          
          // rc-dialog sets display:none on .ant-modal-wrap (inline style). Global getComputedStyle
          // is mocked in test/setup.ts, so assert .style.display instead of toHaveStyle.
          await waitFor(() => {
            const wrap = document.querySelector('.ant-modal-wrap');
            expect(wrap?.style?.display).toBe('none');
          }, { timeout: 3000 });
        }
      }
    });

    it('closes comparison modal when cancel icon clicked', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            expect(screen.getByText('aiTrial.comparisonModal.title')).toBeInTheDocument();
          });
          
          const modal = screen.getByText('aiTrial.comparisonModal.title').closest('.ant-modal');
          const closeIcon = modal?.querySelector('.ant-modal-close');
          
          if (closeIcon) {
            fireEvent.click(closeIcon);
            
            await waitFor(() => {
              const wrap = document.querySelector('.ant-modal-wrap');
              expect(wrap?.style?.display).toBe('none');
            }, { timeout: 3000 });
          }
        }
      }
    });

    it('displays comparison modal with correct width', async () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          await waitFor(() => {
            const dialog = screen.getByRole('dialog', { hidden: true });
            expect((dialog as HTMLElement).style.width).toBe('800px');
          });
        }
      }
    });
  });

  // ============================================================================
  // Create Trial Button Tests
  // ============================================================================

  describe('Create Trial Button', () => {
    it('displays create trial button', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('aiTrial.createNew')).toBeInTheDocument();
    });

    it('calls onCreateTrial when create button clicked', () => {
      const onCreateTrial = vi.fn();
      render(<AITrialDashboard {...defaultProps} onCreateTrial={onCreateTrial} />);
      
      const createButton = screen.getByText('aiTrial.createNew');
      fireEvent.click(createButton);
      
      expect(onCreateTrial).toHaveBeenCalled();
    });

    it('displays create icon in create button', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const createIcon = container.querySelector('[aria-label="plus"]');
      expect(createIcon).toBeInTheDocument();
    });

    it('create button is styled as primary', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const createButton = screen.getByText('aiTrial.createNew').closest('button');
      expect(createButton).toHaveClass('ant-btn-primary');
    });
  });

  // ============================================================================
  // Status Color Coding Tests
  // ============================================================================

  describe('Status Color Coding', () => {
    it('displays created status with default color', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const createdTag = screen.getByText('aiTrial.status.created').closest('.ant-tag');
      expect(createdTag).toHaveClass('ant-tag-default');
    });

    it('displays running status with processing color', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const runningTag = screen.getByText('aiTrial.status.running').closest('.ant-tag');
      expect(runningTag).toHaveClass('ant-tag-processing');
    });

    it('displays completed status with success color', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const completedTags = screen.getAllByText('aiTrial.status.completed');
      const completedTag = completedTags[0].closest('.ant-tag');
      expect(completedTag).toHaveClass('ant-tag-success');
    });

    it('displays failed status with error color', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const failedTag = screen.getByText('aiTrial.status.failed').closest('.ant-tag');
      expect(failedTag).toHaveClass('ant-tag-error');
    });
  });

  // ============================================================================
  // Pagination Tests
  // ============================================================================

  describe('Pagination', () => {
    it('displays pagination controls', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      expect(screen.getByText('Total 5 items')).toBeInTheDocument();
    });

    it('calls onPageChange when page is changed', async () => {
      const onPageChange = vi.fn();
      render(
        <AITrialDashboard
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={onPageChange}
        />
      );
      
      const nextButton = screen.getByTitle('Next Page');
      fireEvent.click(nextButton);
      
      await waitFor(() => {
        expect(onPageChange).toHaveBeenCalledWith(2, 10);
      });
    });

    it('displays correct current page', () => {
      render(
        <AITrialDashboard
          {...defaultProps}
          pagination={{ page: 2, pageSize: 10, total: 50 }}
        />
      );
      
      const activePageItem = screen.getByTitle('2');
      expect(activePageItem).toHaveClass('ant-pagination-item-active');
    });

    it('disables next button on last page', () => {
      render(
        <AITrialDashboard
          {...defaultProps}
          pagination={{ page: 5, pageSize: 10, total: 50 }}
        />
      );
      
      const nextButton = screen.getByTitle('Next Page');
      expect(nextButton).toHaveClass('ant-pagination-disabled');
    });

    it('disables previous button on first page', () => {
      render(
        <AITrialDashboard
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
        />
      );
      
      const prevButton = screen.getByTitle('Previous Page');
      expect(prevButton).toHaveClass('ant-pagination-disabled');
    });

    it('hides pagination when pagination prop is not provided', () => {
      const { container } = render(
        <AITrialDashboard {...defaultProps} pagination={undefined} />
      );
      
      const pagination = container.querySelector('.ant-pagination');
      expect(pagination).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles trials without completedAt date', () => {
      const trialsWithoutCompletedAt: AITrial[] = [
        {
          id: 'trial-no-completed',
          name: 'Trial Without Completed Date',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'running',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={trialsWithoutCompletedAt} />);
      
      expect(screen.getByText('Trial Without Completed Date')).toBeInTheDocument();
    });

    it('handles trials without results', () => {
      const trialsWithoutResults: AITrial[] = [
        {
          id: 'trial-no-results',
          name: 'Trial Without Results',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'completed',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
          completedAt: '2024-01-01T12:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={trialsWithoutResults} />);
      
      expect(screen.getByText('Trial Without Results')).toBeInTheDocument();
    });

    it('handles empty config object', () => {
      const trialsWithEmptyConfig: AITrial[] = [
        {
          id: 'trial-empty-config',
          name: 'Trial With Empty Config',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'created',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={trialsWithEmptyConfig} />);
      
      expect(screen.getByText('Trial With Empty Config')).toBeInTheDocument();
    });

    it('handles very long trial names', () => {
      const trialsWithLongNames: AITrial[] = [
        {
          id: 'trial-long-name',
          name: 'This is a very long trial name that should be displayed correctly without breaking the layout or causing any issues',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'created',
          config: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<AITrialDashboard {...defaultProps} trials={trialsWithLongNames} />);
      
      expect(screen.getByText(/This is a very long trial name/)).toBeInTheDocument();
    });

    it('handles missing optional callbacks gracefully', () => {
      const propsWithoutCallbacks: AITrialDashboardProps = {
        trials: mockTrials,
        loading: false,
      };
      
      render(<AITrialDashboard {...propsWithoutCallbacks} />);
      
      expect(screen.getByText('Grammar Check Trial')).toBeInTheDocument();
    });

    it('handles clicking execute button without onExecute callback', () => {
      const propsWithoutExecute: AITrialDashboardProps = {
        trials: mockTrials,
        loading: false,
      };
      
      render(<AITrialDashboard {...propsWithoutExecute} />);
      
      const executeButton = screen.getByText('aiTrial.actions.execute');
      fireEvent.click(executeButton);
      
      // Should not throw error
      expect(screen.getByText('aiTrial.actions.execute')).toBeInTheDocument();
    });

    it('handles clicking view results button without onViewResults callback', () => {
      const propsWithoutViewResults: AITrialDashboardProps = {
        trials: mockTrials,
        loading: false,
      };
      
      render(<AITrialDashboard {...propsWithoutViewResults} />);
      
      const viewResultsButtons = screen.getAllByText('aiTrial.actions.viewResults');
      fireEvent.click(viewResultsButtons[0]);
      
      // Should not throw error
      expect(screen.getAllByText('aiTrial.actions.viewResults').length).toBe(2);
    });

    it('handles clicking compare button without onCompare callback', () => {
      const { container } = render(
        <AITrialDashboard trials={mockTrials} loading={false} />
      );
      
      const rows = container.querySelectorAll('tbody tr');
      
      const completedRow1 = Array.from(rows).find(row => 
        row.textContent?.includes('Content Enhancement Trial')
      );
      const completedRow2 = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Trial')
      );
      
      const checkbox1 = completedRow1?.querySelector('input[type="checkbox"]');
      const checkbox2 = completedRow2?.querySelector('input[type="checkbox"]');
      
      if (checkbox1 && checkbox2) {
        fireEvent.click(checkbox1);
        fireEvent.click(checkbox2);
        
        const compareButton = screen.getByText('aiTrial.compare').closest('button');
        if (compareButton) {
          fireEvent.click(compareButton);
          
          // Should not throw error
          expect(screen.getByText('aiTrial.compare')).toBeInTheDocument();
        }
      }
    });

    it('handles zero trials correctly', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} trials={[]} />);
      
      // Find the total trials statistic card specifically
      const totalTrialsCard = Array.from(container.querySelectorAll('.ant-statistic-title'))
        .find(el => el.textContent === 'aiTrial.statistics.totalTrials');
      
      const totalTrialsValue = totalTrialsCard?.closest('.ant-statistic')
        ?.querySelector('.ant-statistic-content-value-int');
      
      expect(totalTrialsValue?.textContent).toBe('0');
    });

    it('handles all trials with same status', () => {
      const allCompletedTrials: AITrial[] = [
        {
          id: 'trial-1',
          name: 'Trial 1',
          dataStage: 'sample_library',
          aiModel: 'GPT-4',
          status: 'completed',
          config: {},
          results: {},
          createdBy: 'user-1',
          createdAt: '2024-01-01T10:00:00Z',
          completedAt: '2024-01-01T12:00:00Z',
        },
        {
          id: 'trial-2',
          name: 'Trial 2',
          dataStage: 'annotated',
          aiModel: 'Claude-3',
          status: 'completed',
          config: {},
          results: {},
          createdBy: 'user-1',
          createdAt: '2024-01-02T10:00:00Z',
          completedAt: '2024-01-02T12:00:00Z',
        },
      ];
      
      const { container } = render(<AITrialDashboard {...defaultProps} trials={allCompletedTrials} />);
      
      // Find the total trials statistic card specifically
      const totalTrialsCard = Array.from(container.querySelectorAll('.ant-statistic-title'))
        .find(el => el.textContent === 'aiTrial.statistics.totalTrials');
      
      const totalTrialsValue = totalTrialsCard?.closest('.ant-statistic')
        ?.querySelector('.ant-statistic-content-value-int');
      
      expect(totalTrialsValue?.textContent).toBe('2');
    });
  });

  // ============================================================================
  // Accessibility Tests
  // ============================================================================

  describe('Accessibility', () => {
    it('has proper button roles', () => {
      render(<AITrialDashboard {...defaultProps} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('has proper checkbox roles', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it('displays icons with proper anticon classes', () => {
      const { container } = render(<AITrialDashboard {...defaultProps} />);
      
      expect(container.querySelector('.anticon-plus')).toBeInTheDocument();
      expect(container.querySelector('.anticon-swap')).toBeInTheDocument();
      expect(container.querySelector('.anticon-play-circle')).toBeInTheDocument();
      expect(container.querySelector('.anticon-bar-chart')).toBeInTheDocument();
    });
  });
});
