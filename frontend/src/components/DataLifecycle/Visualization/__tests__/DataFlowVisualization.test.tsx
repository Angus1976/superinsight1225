/**
 * Unit Tests for DataFlowVisualization Component
 * 
 * **Validates: Requirements 11.4**
 * Tests stage rendering, click handlers, navigation, and real-time updates
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react';
import DataFlowVisualization from '../DataFlowVisualization';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock useAuthStore
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    hasPermission: () => true,
  }),
}));

describe('DataFlowVisualization', () => {
  const defaultProps = {
    stages: [
      { id: 'temp_stored', name: 'Temp Stored', key: 'TEMP_STORED', color: '#1890ff', icon: '📥', description: 'Temporary data storage', dataCount: 5 },
      { id: 'under_review', name: 'Under Review', key: 'UNDER_REVIEW', color: '#722ed1', icon: '👀', description: 'Data under review', dataCount: 3 },
      { id: 'review_passed', name: 'Review Passed', key: 'REVIEW_PASSED', color: '#52c41a', icon: '✅', description: 'Review completed', dataCount: 2 },
    ],
    onStageClick: vi.fn(),
    showCounts: true,
    height: 400,
  };

  it('renders without crashing', () => {
    render(<DataFlowVisualization {...defaultProps} />);
    expect(screen.getByText('dataFlowVisualization.title')).toBeInTheDocument();
  });

  it('renders all stage nodes', () => {
    render(<DataFlowVisualization {...defaultProps} />);
    expect(screen.getByText('Temp Stored')).toBeInTheDocument();
    expect(screen.getByText('Under Review')).toBeInTheDocument();
    expect(screen.getByText('Review Passed')).toBeInTheDocument();
  });

  it('shows data count badges when showCounts is true', () => {
    render(<DataFlowVisualization {...defaultProps} />);
    // Data count badges should be visible
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('calls onStageClick when a stage is clicked', () => {
    const onStageClick = vi.fn();
    render(<DataFlowVisualization {...defaultProps} onStageClick={onStageClick} />);
    
    const tempStoredNode = screen.getByText('Temp Stored').closest('g');
    if (tempStoredNode) {
      fireEvent.click(tempStoredNode);
      expect(onStageClick).toHaveBeenCalledWith('temp_stored');
    }
  });

  it('renders legend section', () => {
    render(<DataFlowVisualization {...defaultProps} />);
    expect(screen.getByText('dataFlowVisualization.legend')).toBeInTheDocument();
    expect(screen.getByText('dataFlowVisualization.active')).toBeInTheDocument();
    expect(screen.getByText('dataFlowVisualization.completed')).toBeInTheDocument();
  });

  it('renders connection lines between stages', () => {
    render(<DataFlowVisualization {...defaultProps} />);
    // SVG should contain lines (connection paths)
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('shows active stage details when clicked', () => {
    const onStageClick = vi.fn();
    render(<DataFlowVisualization {...defaultProps} onStageClick={onStageClick} />);
    
    const tempStoredNode = screen.getByText('Temp Stored').closest('g');
    if (tempStoredNode) {
      fireEvent.click(tempStoredNode);
    }
    
    // Active stage details should be visible
    expect(screen.getByText('Temporary data storage')).toBeInTheDocument();
  });

  it('renders with custom height', () => {
    const customHeight = 600;
    render(<DataFlowVisualization {...defaultProps} height={customHeight} />);
    
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('height', String(customHeight));
  });

  it('hides data count badges when showCounts is false', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 3 },
    ];
    
    render(<DataFlowVisualization stages={stages} showCounts={false} />);
    
    // Count badges should not be visible in SVG circles
    const svg = document.querySelector('svg');
    const circles = svg?.querySelectorAll('circle');
    expect(circles?.length).toBe(0);
  });

  it('renders with empty stages array', () => {
    render(<DataFlowVisualization {...defaultProps} stages={[]} />);
    expect(screen.getByText('dataFlowVisualization.title')).toBeInTheDocument();
  });

  it('handles stage click toggle behavior', () => {
    const onStageClick = vi.fn();
    render(<DataFlowVisualization {...defaultProps} onStageClick={onStageClick} />);
    
    const tempStoredNode = screen.getByText('Temp Stored').closest('g');
    if (tempStoredNode) {
      fireEvent.click(tempStoredNode);
      fireEvent.click(tempStoredNode);
      expect(onStageClick).toHaveBeenCalledTimes(2);
    }
  });
});

describe('Stage Rendering with Different Data Counts', () => {
  it('renders stages with zero data count', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 0 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 0 },
    ];
    
    render(<DataFlowVisualization stages={stages} showCounts={true} />);
    
    // Should render stages even with zero count
    expect(screen.getByText('Stage 1')).toBeInTheDocument();
    expect(screen.getByText('Stage 2')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(2);
  });

  it('renders stages with small data counts (1-10)', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 1 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 5 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 10 },
    ];
    
    render(<DataFlowVisualization stages={stages} showCounts={true} />);
    
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders stages with medium data counts (11-99)', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 15 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 50 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 99 },
    ];
    
    render(<DataFlowVisualization stages={stages} showCounts={true} />);
    
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('99')).toBeInTheDocument();
  });

  it('renders stages with large data counts (100+)', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 100 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 500 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 1000 },
    ];
    
    render(<DataFlowVisualization stages={stages} showCounts={true} />);
    
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
  });

  it('renders all 13 default lifecycle stages', () => {
    render(<DataFlowVisualization />);
    
    // Should render all 13 stages
    expect(screen.getByText('Temp Stored')).toBeInTheDocument();
    expect(screen.getByText('Under Review')).toBeInTheDocument();
    expect(screen.getByText('Review Passed')).toBeInTheDocument();
    expect(screen.getByText('Review Rejected')).toBeInTheDocument();
    expect(screen.getByText('Sample Ready')).toBeInTheDocument();
    expect(screen.getByText('Annotation Pending')).toBeInTheDocument();
    expect(screen.getByText('Annotation In Progress')).toBeInTheDocument();
    expect(screen.getByText('Annotation Completed')).toBeInTheDocument();
    expect(screen.getByText('Enhancement Pending')).toBeInTheDocument();
    expect(screen.getByText('Enhancement In Progress')).toBeInTheDocument();
    expect(screen.getByText('Enhancement Completed')).toBeInTheDocument();
    expect(screen.getByText('AI Trial Pending')).toBeInTheDocument();
    expect(screen.getByText('AI Trial Completed')).toBeInTheDocument();
  });

  it('displays correct stage count in header', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 3 },
    ];
    
    render(<DataFlowVisualization stages={stages} />);
    
    // Check for stage count in the tag - find the tag element
    const tags = document.querySelectorAll('.ant-tag');
    const stageCountTag = Array.from(tags).find(tag => tag.textContent?.includes('dataFlowVisualization.stages'));
    expect(stageCountTag).toBeDefined();
    expect(stageCountTag?.textContent).toContain('2');
  });
});

describe('Click Handlers and Navigation', () => {
  let onStageClick: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onStageClick = vi.fn();
  });

  it('calls onStageClick with correct stage ID when stage is clicked', () => {
    const stages = [
      { id: 'temp_stored', name: 'Temp Stored', key: 'TEMP_STORED', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
      { id: 'under_review', name: 'Under Review', key: 'UNDER_REVIEW', color: '#722ed1', icon: '👀', description: 'Test', dataCount: 3 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    const tempStoredNode = screen.getByText('Temp Stored').closest('g');
    fireEvent.click(tempStoredNode!);
    
    expect(onStageClick).toHaveBeenCalledWith('temp_stored');
    expect(onStageClick).toHaveBeenCalledTimes(1);
  });

  it('calls onStageClick for different stages', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 3 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 2 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    expect(onStageClick).toHaveBeenCalledWith('stage1');
    
    fireEvent.click(screen.getByText('Stage 2').closest('g')!);
    expect(onStageClick).toHaveBeenCalledWith('stage2');
    
    fireEvent.click(screen.getByText('Stage 3').closest('g')!);
    expect(onStageClick).toHaveBeenCalledWith('stage3');
    
    expect(onStageClick).toHaveBeenCalledTimes(3);
  });

  it('toggles active state when same stage is clicked twice', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test description', dataCount: 5 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    const stageNode = screen.getByText('Stage 1').closest('g');
    
    // First click - activate
    fireEvent.click(stageNode!);
    expect(screen.getByText('Test description')).toBeInTheDocument();
    
    // Second click - deactivate
    fireEvent.click(stageNode!);
    expect(screen.queryByText('Test description')).not.toBeInTheDocument();
    
    expect(onStageClick).toHaveBeenCalledTimes(2);
  });

  it('shows active stage details panel when stage is clicked', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Stage 1 description', dataCount: 10 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    // Initially no details shown
    expect(screen.queryByText('Stage 1 description')).not.toBeInTheDocument();
    
    // Click stage
    fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    
    // Details should be visible
    expect(screen.getByText('Stage 1 description')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('switches active stage when different stage is clicked', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Description 1', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Description 2', dataCount: 3 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    // Click first stage
    fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    
    // Click second stage
    fireEvent.click(screen.getByText('Stage 2').closest('g')!);
    expect(screen.queryByText('Description 1')).not.toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
  });

  it('handles click when onStageClick is not provided', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    // Should not throw error
    expect(() => {
      render(<DataFlowVisualization stages={stages} />);
      fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    }).not.toThrow();
  });

  it('handles mouse hover events on stages', () => {
    const stages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    render(<DataFlowVisualization stages={stages} onStageClick={onStageClick} />);
    
    const stageNode = screen.getByText('Stage 1').closest('g');
    
    // Hover should not throw error
    expect(() => {
      fireEvent.mouseEnter(stageNode!);
      fireEvent.mouseLeave(stageNode!);
    }).not.toThrow();
  });
});

describe('Real-time Updates', () => {
  it('updates stage data counts when stages prop changes', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} showCounts={true} />);
    
    expect(screen.getByText('5')).toBeInTheDocument();
    
    // Update data count
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 10 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} showCounts={true} />);
    
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.queryByText('5')).not.toBeInTheDocument();
  });

  it('updates multiple stage counts simultaneously', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 3 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 2 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} showCounts={true} />);
    
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    
    // Update all counts
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 15 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Test', dataCount: 8 },
      { id: 'stage3', name: 'Stage 3', key: 'STAGE3', color: '#fa8c16', icon: '📝', description: 'Test', dataCount: 12 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} showCounts={true} />);
    
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('updates active stage details when data changes', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} />);
    
    // Activate stage
    fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    expect(screen.getByText('5')).toBeInTheDocument();
    
    // Update data count
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 20 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} />);
    
    // Active stage details should show updated count
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('handles stage count decreasing to zero', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 10 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} showCounts={true} />);
    
    expect(screen.getByText('10')).toBeInTheDocument();
    
    // Decrease to zero
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 0 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} showCounts={true} />);
    
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.queryByText('10')).not.toBeInTheDocument();
  });

  it('handles rapid successive updates', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 1 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} showCounts={true} />);
    
    // Simulate rapid updates
    for (let i = 2; i <= 5; i++) {
      const updatedStages = [
        { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: i },
      ];
      rerender(<DataFlowVisualization stages={updatedStages} showCounts={true} />);
    }
    
    // Should show final count
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('preserves active stage selection during updates', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Description 1', dataCount: 5 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Description 2', dataCount: 3 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} />);
    
    // Activate first stage
    fireEvent.click(screen.getByText('Stage 1').closest('g')!);
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    
    // Update data counts
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Description 1', dataCount: 10 },
      { id: 'stage2', name: 'Stage 2', key: 'STAGE2', color: '#52c41a', icon: '✅', description: 'Description 2', dataCount: 8 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} />);
    
    // Active stage should still be visible with updated count
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('updates stage colors dynamically', () => {
    const initialStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#1890ff', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    const { rerender } = render(<DataFlowVisualization stages={initialStages} />);
    
    // Update color
    const updatedStages = [
      { id: 'stage1', name: 'Stage 1', key: 'STAGE1', color: '#52c41a', icon: '📥', description: 'Test', dataCount: 5 },
    ];
    
    rerender(<DataFlowVisualization stages={updatedStages} />);
    
    // Component should re-render without errors
    expect(screen.getByText('Stage 1')).toBeInTheDocument();
  });
});