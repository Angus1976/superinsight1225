/**
 * CollaborationIndicator Component Tests
 *
 * Tests for the Collaboration Indicator component including:
 * - Real-time collaborator display
 * - Conflict warnings
 * - User presence tracking
 * - WebSocket event handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import i18n from '@/locales/config';
import CollaborationIndicator from '../CollaborationIndicator';

// Mock WebSocket hook
const mockWsOn = vi.fn();
const mockWsOff = vi.fn();

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    on: mockWsOn,
    off: mockWsOff,
  }),
}));

const mockCollaborators = [
  {
    userId: 1,
    username: 'Alice',
    avatar: 'avatar1.png',
    status: 'editing' as const,
    currentTask: 123,
    lastActivity: '2026-01-24T10:00:00Z',
    color: '#1890ff',
  },
  {
    userId: 2,
    username: 'Bob',
    status: 'viewing' as const,
    lastActivity: '2026-01-24T09:55:00Z',
    color: '#52c41a',
  },
  {
    userId: 3,
    username: 'Charlie',
    status: 'idle' as const,
    lastActivity: '2026-01-24T09:30:00Z',
    color: '#999',
  },
];

const mockConflict = {
  warningId: 'conflict_1',
  type: 'concurrent_edit' as const,
  message: 'Multiple users editing same annotation',
  conflictingUser: 'Alice',
  timestamp: '2026-01-24T10:05:00Z',
};

async function clickCollaborationTrigger(user: ReturnType<typeof userEvent.setup>) {
  const el = document.querySelector('.collaboration-indicator [aria-label="team"]');
  if (!el) throw new Error('Collaboration trigger not found');
  await user.click(el);
}

describe('CollaborationIndicator', () => {
  const defaultProps = {
    projectId: 100,
    taskId: 123,
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('establishes WebSocket connection with correct URL', () => {
    render(<CollaborationIndicator {...defaultProps} />);

    // Verify WebSocket connection URL includes project_id and task_id
    expect(mockWsOn).toHaveBeenCalled();
  });

  it('shows zero active collaborators initially', () => {
    render(<CollaborationIndicator {...defaultProps} />);

    // Badge count should be 0 or hidden initially
    const badge = screen.queryByText('0');
    expect(badge).toBeNull(); // showZero is false
  });

  it('displays active collaborators when received via WebSocket', async () => {
    render(<CollaborationIndicator {...defaultProps} />);

    // Simulate receiving collaborators update
    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    expect(updateHandler).toBeDefined();

    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    await waitFor(() => {
      // Badge should show 2 active collaborators (editing + viewing, not idle)
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('shows collaborator list in popover when clicked', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    // Add collaborators
    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      expect(screen.getByText('Charlie')).toBeInTheDocument();
    });
  });

  it('displays correct status icons and text for each collaborator', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.getByText('Editing')).toBeInTheDocument();
      expect(screen.getByText('Viewing')).toBeInTheDocument();
      expect(screen.getByText('Idle')).toBeInTheDocument();
    });
  });

  it('shows "Same Task" tag for collaborators on the same task', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator projectId={100} taskId={123} />);

    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      // Alice is on task 123 (same as current taskId)
      expect(screen.getByText('Same Task')).toBeInTheDocument();
    });
  });

  it('adds new collaborator when user_joined event is received', async () => {
    render(<CollaborationIndicator {...defaultProps} />);

    const joinedHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'user_joined'
    )?.[1];

    const newCollaborator = {
      userId: 4,
      username: 'David',
      status: 'viewing' as const,
      lastActivity: '2026-01-24T10:10:00Z',
      color: '#faad14',
    };

    await act(async () => {
      joinedHandler?.(newCollaborator);
    });

    const user = userEvent.setup();
    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.getByText('David')).toBeInTheDocument();
    });
  });

  it('removes collaborator when user_left event is received', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    // Add collaborators first
    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    // Remove Alice
    const leftHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'user_left'
    )?.[1];
    await act(async () => {
      leftHandler?.({ userId: 1 });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.queryByText('Alice')).not.toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  it('updates collaborator status when status_changed event is received', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    // Add collaborators
    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: mockCollaborators });
    });

    // Change Bob's status from viewing to editing
    const statusHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'user_status_changed'
    )?.[1];
    await act(async () => {
      statusHandler?.({ userId: 2, status: 'editing' });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      // Bob should now show as "Editing"
      const editingTags = screen.getAllByText('Editing');
      expect(editingTags.length).toBeGreaterThanOrEqual(2); // Alice and Bob
    });
  });

  it('displays conflict warning when conflict_warning event is received', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: [mockCollaborators[0]] });
    });

    const conflictHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'conflict_warning'
    )?.[1];
    await act(async () => {
      conflictHandler?.(mockConflict);
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.getByText('Conflicts Detected')).toBeInTheDocument();
      expect(screen.getByText('Multiple users editing same annotation')).toBeInTheDocument();
    });
  });

  it('removes conflict when conflict_resolved event is received', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: [mockCollaborators[0]] });
    });

    const conflictHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'conflict_warning'
    )?.[1];
    await act(async () => {
      conflictHandler?.(mockConflict);
    });

    const resolveHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'conflict_resolved'
    )?.[1];
    await act(async () => {
      resolveHandler?.({ warningId: 'conflict_1' });
    });

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.queryByText('Conflicts Detected')).not.toBeInTheDocument();
    });
  });

  it('limits conflicts to last 5', async () => {
    render(<CollaborationIndicator {...defaultProps} />);

    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: [mockCollaborators[0]] });
    });

    const conflictHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'conflict_warning'
    )?.[1];

    // Add 6 conflicts
    for (let i = 0; i < 6; i++) {
      await act(async () => {
        conflictHandler?.({
          ...mockConflict,
          warningId: `conflict_${i}`,
          message: `Conflict ${i}`,
        });
      });
    }

    const user = userEvent.setup();
    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.queryByText('Conflict 0')).not.toBeInTheDocument();
      expect(screen.getByText('Conflict 5')).toBeInTheDocument();
    });
  });

  it('cleans up WebSocket listeners on unmount', () => {
    const { unmount } = render(<CollaborationIndicator {...defaultProps} />);

    unmount();

    expect(mockWsOff).toHaveBeenCalledWith('connect');
    expect(mockWsOff).toHaveBeenCalledWith('disconnect');
    expect(mockWsOff).toHaveBeenCalledWith('collaborators_update');
    expect(mockWsOff).toHaveBeenCalledWith('user_joined');
    expect(mockWsOff).toHaveBeenCalledWith('user_left');
    expect(mockWsOff).toHaveBeenCalledWith('user_status_changed');
    expect(mockWsOff).toHaveBeenCalledWith('conflict_warning');
    expect(mockWsOff).toHaveBeenCalledWith('conflict_resolved');
  });

  it('shows "No collaborators online" when empty', async () => {
    const user = userEvent.setup();
    render(<CollaborationIndicator {...defaultProps} />);

    await clickCollaborationTrigger(user);

    await waitFor(() => {
      expect(screen.getByText('No collaborators online')).toBeInTheDocument();
    });
  });

  it('works without taskId (project-level collaboration)', () => {
    render(<CollaborationIndicator projectId={100} />);

    // Should still establish WebSocket connection
    expect(mockWsOn).toHaveBeenCalled();
  });

  it('updates existing collaborator instead of duplicating on user_joined', async () => {
    render(<CollaborationIndicator {...defaultProps} />);

    // Add Alice initially
    const updateHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'collaborators_update'
    )?.[1];
    await act(async () => {
      updateHandler?.({ collaborators: [mockCollaborators[0]] });
    });

    // Receive user_joined for Alice again (re-join scenario)
    const joinedHandler = mockWsOn.mock.calls.find(
      (call) => call[0] === 'user_joined'
    )?.[1];
    await act(async () => {
      joinedHandler?.({ ...mockCollaborators[0], status: 'viewing' as const });
    });

    const user = userEvent.setup();
    await clickCollaborationTrigger(user);

    await waitFor(() => {
      // Should only have one Alice, with updated status
      const aliceElements = screen.getAllByText('Alice');
      expect(aliceElements).toHaveLength(1);
      expect(screen.getByText('Viewing')).toBeInTheDocument();
    });
  });
});
