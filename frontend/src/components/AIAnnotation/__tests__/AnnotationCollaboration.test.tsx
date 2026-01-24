/**
 * AnnotationCollaboration Component Tests
 *
 * Tests for the Annotation Collaboration component including:
 * - Component rendering
 * - WebSocket connection management
 * - AI suggestion display
 * - User presence tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@/test/test-utils';
import AnnotationCollaboration from '../AnnotationCollaboration';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: Event) => void) | null = null;
  readyState = MockWebSocket.CONNECTING;
  
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    // Auto-connect after a short delay to simulate real WebSocket behavior
    setTimeout(() => {
      if (this.readyState === MockWebSocket.CONNECTING) {
        this.connect();
      }
    }, 10);
  }
  
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  });
  
  connect() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }
  
  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
  
  static clearInstances() {
    MockWebSocket.instances = [];
  }
}

// Mock window.location for WebSocket URL construction
Object.defineProperty(window, 'location', {
  value: {
    protocol: 'http:',
    host: 'localhost:3000',
    hostname: 'localhost',
    port: '3000',
    pathname: '/',
    search: '',
    hash: '',
    href: 'http://localhost:3000/',
  },
  writable: true,
});

// @ts-ignore - Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        'ai_annotation:collaboration.connected': 'Connected to collaboration server',
        'ai_annotation:collaboration.connecting': 'Connecting to collaboration server...',
        'ai_annotation:collaboration.disconnected': 'Disconnected from collaboration server',
        'ai_annotation:collaboration.ai_suggestions': 'AI Suggestions',
        'ai_annotation:collaboration.no_suggestions': 'No AI suggestions yet. Start annotating to receive suggestions.',
        'ai_annotation:collaboration.conflicts': 'Annotation Conflicts',
        'ai_annotation:collaboration.online_users': 'Online Users',
        'ai_annotation:collaboration.no_users_online': 'No other users online',
        'ai_annotation:collaboration.progress': 'Progress',
        'ai_annotation:collaboration.completion': 'Completion',
        'ai_annotation:collaboration.completed': 'Completed',
        'ai_annotation:collaboration.in_progress': 'In Progress',
        'ai_annotation:collaboration.annotators': 'Annotators',
        'ai_annotation:collaboration.avg_time': 'Avg Time',
        'ai_annotation:collaboration.confidence': 'Confidence',
        'ai_annotation:collaboration.suggestion_accepted': 'Suggestion accepted',
        'ai_annotation:collaboration.suggestion_rejected': 'Suggestion rejected',
        'ai_annotation:collaboration.accept_failed': 'Failed to accept suggestion',
        'ai_annotation:collaboration.reject_failed': 'Failed to reject suggestion',
        'ai_annotation:collaboration.reject_suggestion': 'Reject Suggestion',
        'ai_annotation:collaboration.reject_reason': 'Reason for rejection',
        'ai_annotation:collaboration.reject_reason_placeholder': 'Enter reason for rejecting this suggestion (optional)',
        'ai_annotation:collaboration.conflict_resolved': 'Conflict resolved successfully',
        'ai_annotation:collaboration.resolve_failed': 'Failed to resolve conflict',
        'ai_annotation:collaboration.resolve_conflict': 'Resolve Conflict',
        'ai_annotation:collaboration.conflict_description': 'Multiple annotators have provided different annotations for the same content.',
        'ai_annotation:collaboration.conflicting_annotations': 'Conflicting Annotations',
        'ai_annotation:collaboration.position': 'Position',
        'ai_annotation:collaboration.by': 'By',
        'ai_annotation:collaboration.or': 'Or',
        'ai_annotation:collaboration.create_custom': 'Create Custom Annotation',
        'ai_annotation:collaboration.reject_all': 'Reject All',
        'ai_annotation:collaboration.label': 'Label',
        'ai_annotation:collaboration.text': 'Text',
        'ai_annotation:collaboration.apply_resolution': 'Apply Resolution',
        'ai_annotation:collaboration.document': 'Document',
        'ai_annotation:collaboration.working_on': `Working on: ${options?.doc || ''}`,
        'ai_annotation:collaboration.status.pending': 'Pending',
        'ai_annotation:collaboration.status.accepted': 'Accepted',
        'ai_annotation:collaboration.status.rejected': 'Rejected',
        'ai_annotation:collaboration.status.online': 'Online',
        'ai_annotation:collaboration.status.idle': 'Idle',
        'ai_annotation:collaboration.status.annotating': 'Annotating',
        'ai_annotation:collaboration.conflict_types.overlap': 'Overlapping Annotations',
        'ai_annotation:collaboration.conflict_types.label_mismatch': 'Label Mismatch',
        'ai_annotation:collaboration.conflict_types.boundary': 'Boundary Disagreement',
        'common:actions.confirm': 'Confirm',
        'common:actions.cancel': 'Cancel',
        'common:actions.reconnect': 'Reconnect',
        'common:actions.clear': 'Clear',
        'common:actions.accept': 'Accept',
        'common:actions.reject': 'Reject',
        'common:actions.resolve': 'Resolve',
        'common:unknown': 'Unknown',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const mockProgress = {
  totalTasks: 100,
  completedTasks: 45,
  inProgressTasks: 10,
  pendingTasks: 45,
  completionRate: 0.45,
  avgTimePerTaskMinutes: 2.5,
  activeAnnotators: 3,
  activeReviewers: 1,
};

describe('AnnotationCollaboration', () => {
  const defaultProps = {
    projectId: 'project_1',
    documentId: 'doc_1',
    onSuggestionAccept: vi.fn(),
    onSuggestionReject: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.clearInstances();
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/progress/')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockProgress,
        });
      }
      if (url.includes('/conflicts/')) {
        return Promise.resolve({
          ok: true,
          json: async () => [], // Return empty array for conflicts
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    MockWebSocket.clearInstances();
  });

  it('renders collaboration panel with AI Suggestions section', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('AI Suggestions')).toBeInTheDocument();
    });
  });

  it('renders collaboration panel with Online Users section', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Online Users')).toBeInTheDocument();
    });
  });

  it('shows connecting or connected status after mount', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    // After mount, the component should either be connecting or connected
    // (since WebSocket auto-connects in the mock)
    await waitFor(() => {
      const connectedText = screen.queryByText('Connected to collaboration server');
      const connectingText = screen.queryByText('Connecting to collaboration server...');
      expect(connectedText || connectingText).toBeTruthy();
    });
  });

  it('establishes WebSocket connection on mount', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    expect(MockWebSocket.instances[0].url).toContain('/api/v1/annotation/ws');
  });

  it('shows connected status when WebSocket connects', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    // Wait for WebSocket to be created and auto-connect
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    // Wait for auto-connect to complete
    await waitFor(() => {
      expect(screen.getByText('Connected to collaboration server')).toBeInTheDocument();
    });
  });

  it('displays empty state when no suggestions', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('No AI suggestions yet. Start annotating to receive suggestions.')).toBeInTheDocument();
    });
  });

  it('shows no users online message when user list is empty', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('No other users online')).toBeInTheDocument();
    });
  });

  it('closes WebSocket connection on unmount', async () => {
    const { unmount } = render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    const ws = MockWebSocket.instances[0];
    unmount();
    
    expect(ws.close).toHaveBeenCalled();
  });

  it('sends authentication message when WebSocket connects', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    // Wait for auto-connect and authentication
    await waitFor(() => {
      expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('authenticate')
      );
    });
  });

  it('displays online users when received via WebSocket', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    // Wait for auto-connect
    await waitFor(() => {
      expect(MockWebSocket.instances[0].readyState).toBe(MockWebSocket.OPEN);
    });
    
    // Simulate receiving online user
    await act(async () => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'user_joined',
        payload: { 
          id: 'user_1', 
          name: 'Alice', 
          status: 'annotating', 
          currentDocument: 'doc_1', 
          lastActivity: '2026-01-24T10:00:00Z' 
        },
      });
    });
    
    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
    });
  });

  it('displays progress metrics when received via WebSocket', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    // Wait for auto-connect
    await waitFor(() => {
      expect(MockWebSocket.instances[0].readyState).toBe(MockWebSocket.OPEN);
    });
    
    // Simulate receiving progress
    await act(async () => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'progress_update',
        payload: mockProgress,
      });
    });
    
    await waitFor(() => {
      expect(screen.getByText('Progress')).toBeInTheDocument();
    });
  });

  it('displays AI suggestions when received via WebSocket', async () => {
    render(<AnnotationCollaboration {...defaultProps} />);
    
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });
    
    // Wait for auto-connect
    await waitFor(() => {
      expect(MockWebSocket.instances[0].readyState).toBe(MockWebSocket.OPEN);
    });
    
    // Simulate receiving suggestion
    await act(async () => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'suggestion',
        payload: {
          id: 'sug_1',
          documentId: 'doc_1',
          text: 'John Doe is the CEO of Acme Corp',
          annotations: [
            { label: 'PERSON', start: 0, end: 8, text: 'John Doe', confidence: 0.95 },
          ],
          confidence: 0.95,
          latencyMs: 150,
          timestamp: '2026-01-24T10:00:00Z',
          status: 'pending',
        },
      });
    });
    
    await waitFor(() => {
      expect(screen.getByText(/PERSON/)).toBeInTheDocument();
    });
  });
});
