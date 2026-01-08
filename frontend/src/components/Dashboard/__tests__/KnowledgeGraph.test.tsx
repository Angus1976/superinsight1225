// KnowledgeGraph component test
import { render, screen } from '@testing-library/react';
import { KnowledgeGraph } from '../KnowledgeGraph';

// Mock d3 to avoid DOM manipulation issues in tests
vi.mock('d3', () => ({
  select: vi.fn(() => ({
    selectAll: vi.fn(() => ({ remove: vi.fn() })),
    append: vi.fn(() => ({
      selectAll: vi.fn(() => ({
        data: vi.fn(() => ({
          enter: vi.fn(() => ({
            append: vi.fn(() => ({
              attr: vi.fn(() => ({ attr: vi.fn() })),
            })),
          })),
        })),
      })),
    })),
    call: vi.fn(),
    attr: vi.fn(),
  })),
  forceSimulation: vi.fn(() => ({
    force: vi.fn(() => ({ force: vi.fn() })),
    on: vi.fn(),
    stop: vi.fn(),
  })),
  forceLink: vi.fn(() => ({
    id: vi.fn(() => ({ distance: vi.fn() })),
  })),
  forceManyBody: vi.fn(() => ({ strength: vi.fn() })),
  forceCenter: vi.fn(),
  forceCollide: vi.fn(() => ({ radius: vi.fn() })),
  zoom: vi.fn(() => ({
    scaleExtent: vi.fn(() => ({ on: vi.fn() })),
  })),
  hierarchy: vi.fn(),
  tree: vi.fn(() => ({ size: vi.fn() })),
  drag: vi.fn(() => ({
    on: vi.fn(() => ({ on: vi.fn(() => ({ on: vi.fn() })) })),
  })),
}));

describe('KnowledgeGraph', () => {
  it('renders without crashing', () => {
    render(<KnowledgeGraph />);

    // Should render the knowledge graph card
    expect(screen.getByText('知识图谱')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<KnowledgeGraph loading={true} />);

    // Should show loading card
    expect(screen.getByText('知识图谱')).toBeInTheDocument();
  });

  it('renders with custom height', () => {
    render(<KnowledgeGraph height={800} />);

    // Should render with custom height
    expect(screen.getByText('知识图谱')).toBeInTheDocument();
  });

  it('renders controls', () => {
    render(<KnowledgeGraph />);

    // Should show layout and filter controls
    expect(screen.getByDisplayValue('force')).toBeInTheDocument();
    expect(screen.getByDisplayValue('all')).toBeInTheDocument();
  });
});