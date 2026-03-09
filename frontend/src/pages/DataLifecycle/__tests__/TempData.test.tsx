/**
 * TempData Page Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TempDataPage from '../TempData';

// Mock hooks
vi.mock('@/hooks/useDataLifecycle', () => ({
  useTempData: vi.fn(() => ({
    data: [],
    loading: false,
    error: null,
    pagination: { page: 1, pageSize: 10, total: 0 },
    fetchTempData: vi.fn(),
    setFilters: vi.fn(),
    clearFilters: vi.fn(),
  })),
  useReview: vi.fn(() => ({
    submitForReview: vi.fn(),
  })),
}));

// Mock components
vi.mock('@/components/DataLifecycle/TempData/TempDataTable', () => ({
  default: ({ onEdit, onView }: any) => (
    <div data-testid="temp-data-table">
      <button onClick={() => onEdit?.({ id: '1', name: 'Test' })}>Edit</button>
      <button onClick={() => onView?.({ id: '1', name: 'Test' })}>View</button>
    </div>
  ),
}));

vi.mock('@/components/DataLifecycle/Review/ReviewModal', () => ({
  default: ({ visible, onClose }: any) => (
    visible ? (
      <div data-testid="review-modal">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null
  ),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('TempDataPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <TempDataPage />
      </BrowserRouter>
    );
  };

  it('renders page title and description', () => {
    renderComponent();
    
    expect(screen.getByText('tempData.title')).toBeInTheDocument();
    expect(screen.getByText('tempData.description')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderComponent();
    
    expect(screen.getByText('common.actions.refresh')).toBeInTheDocument();
    expect(screen.getByText('tempData.uploadDocument')).toBeInTheDocument();
  });

  it('renders filter controls', () => {
    renderComponent();
    
    // Check for filter button
    expect(screen.getByText('common.actions.filter')).toBeInTheDocument();
    
    // Check for reset button
    expect(screen.getByText('common.actions.reset')).toBeInTheDocument();
  });

  it('renders TempDataTable component', () => {
    renderComponent();
    
    expect(screen.getByTestId('temp-data-table')).toBeInTheDocument();
  });

  it('navigates to upload page when upload button is clicked', () => {
    renderComponent();
    
    const uploadButton = screen.getByText('tempData.uploadDocument');
    fireEvent.click(uploadButton);
    
    expect(mockNavigate).toHaveBeenCalledWith('/data-structuring/upload');
  });

  it('renders breadcrumb navigation', () => {
    renderComponent();
    
    // Breadcrumb should contain navigation items
    const breadcrumbs = screen.getByRole('navigation');
    expect(breadcrumbs).toBeInTheDocument();
  });

  it('displays statistics card', () => {
    renderComponent();
    
    // Should show total count using i18n key
    // The mock returns the key itself, so we check for the pattern
    expect(screen.getByText(/common.pagination.total/i)).toBeInTheDocument();
  });
});
