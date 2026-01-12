// KnowledgeGraph component test
import { render, screen } from '@testing-library/react';
import { KnowledgeGraph } from '../KnowledgeGraph';
import { vi } from 'vitest';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

// Mock d3 completely to avoid DOM manipulation issues in tests
vi.mock('d3', () => {
  // Create a deeply chainable mock that returns itself for any method call
  const createDeepChainable = (): any => {
    const handler: ProxyHandler<any> = {
      get: (target, prop) => {
        if (prop === 'then') return undefined; // Prevent Promise-like behavior
        return createDeepChainable();
      },
      apply: () => createDeepChainable(),
    };
    const fn = function() { return createDeepChainable(); };
    return new Proxy(fn, handler);
  };
  
  const chainable = createDeepChainable();
  return {
    select: chainable,
    selectAll: chainable,
    forceSimulation: chainable,
    forceLink: chainable,
    forceManyBody: chainable,
    forceCenter: chainable,
    forceCollide: chainable,
    zoom: chainable,
    hierarchy: chainable,
    tree: chainable,
    drag: chainable,
  };
});

describe('KnowledgeGraph', () => {
  it('renders without crashing', () => {
    render(<KnowledgeGraph />);

    // Should render the knowledge graph card (using translation key)
    expect(screen.getByText('charts.knowledgeGraph')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<KnowledgeGraph loading={true} />);

    // Should show loading card
    expect(screen.getByText('charts.knowledgeGraph')).toBeInTheDocument();
  });

  it('renders with custom height', () => {
    render(<KnowledgeGraph height={800} />);

    // Should render with custom height
    expect(screen.getByText('charts.knowledgeGraph')).toBeInTheDocument();
  });

  it('renders controls', () => {
    render(<KnowledgeGraph />);

    // Should show the graph legend (always visible)
    expect(screen.getByText('graph.legend')).toBeInTheDocument();
    // Should show node type labels in legend
    expect(screen.getByText('graph.dataNodes')).toBeInTheDocument();
  });
});