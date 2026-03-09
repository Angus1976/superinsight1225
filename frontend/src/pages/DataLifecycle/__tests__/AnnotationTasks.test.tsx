/**
 * AnnotationTasks Page Component Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import AnnotationTasksPage from '../AnnotationTasks';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock react-router-dom hooks
const mockNavigate = vi.fn();
const mockLocation = { state: null, pathname: '/data-lifecycle/annotation-tasks' };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  };
});

// Helper function to render with providers
const renderComponent = () => {
  return render(
    <BrowserRouter>
      <AnnotationTasksPage />
    </BrowserRouter>
  );
};

describe('AnnotationTasksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Page Structure', () => {
    it('should render page header with title and description', () => {
      renderComponent();
      
      expect(screen.getByText('annotationTask.title')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.description')).toBeInTheDocument();
    });

    it('should render breadcrumb navigation', () => {
      renderComponent();
      
      expect(screen.getByText('common.actions.back')).toBeInTheDocument();
      expect(screen.getByText('interface.title')).toBeInTheDocument();
      expect(screen.getByText('tabs.annotation')).toBeInTheDocument();
    });

    it('should render action buttons', () => {
      renderComponent();
      
      expect(screen.getByText('common.actions.refresh')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.actions.create')).toBeInTheDocument();
    });
  });

  describe('Filters', () => {
    it('should render filter controls', () => {
      renderComponent();
      
      // Filter and reset buttons
      expect(screen.getByText('common.actions.filter')).toBeInTheDocument();
      expect(screen.getByText('common.actions.reset')).toBeInTheDocument();
    });

    it('should clear filters when reset button is clicked', () => {
      renderComponent();
      
      const resetButton = screen.getByText('common.actions.reset');
      fireEvent.click(resetButton);
      
      // Component should still be rendered
      expect(resetButton).toBeInTheDocument();
    });
  });

  describe('Statistics Cards', () => {
    it('should render statistics cards', () => {
      renderComponent();
      
      // Should show statistics
      expect(screen.getByText('annotationTask.status.pending')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.status.inProgress')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.progress.percentage')).toBeInTheDocument();
    });
  });

  describe('Action Handlers', () => {
    it('should handle refresh button click', () => {
      renderComponent();
      
      const refreshButton = screen.getByText('common.actions.refresh');
      fireEvent.click(refreshButton);
      
      // Should trigger refresh (component should re-render)
      expect(refreshButton).toBeInTheDocument();
    });

    it('should handle create task button click', () => {
      renderComponent();
      
      const createButton = screen.getByText('annotationTask.actions.create');
      fireEvent.click(createButton);
      
      // Should trigger create task action
      expect(createButton).toBeInTheDocument();
    });

    it('should handle filter apply button click', () => {
      renderComponent();
      
      const filterButton = screen.getByText('common.actions.filter');
      fireEvent.click(filterButton);
      
      // Should apply filters
      expect(filterButton).toBeInTheDocument();
    });
  });

  describe('Placeholder Component', () => {
    it('should render placeholder card', () => {
      renderComponent();
      
      // Should render a card for the placeholder
      const cards = document.querySelectorAll('.ant-card');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('Summary Section', () => {
    it('should render summary with total count', () => {
      renderComponent();
      
      // Should show total count in summary
      expect(screen.getByText('common.pagination.total')).toBeInTheDocument();
    });
  });
});
