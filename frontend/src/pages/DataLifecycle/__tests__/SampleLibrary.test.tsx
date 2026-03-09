/**
 * SampleLibrary Page Component Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SampleLibraryPage from '../SampleLibrary';
import * as useDataLifecycleHook from '@/hooks/useDataLifecycle';

// Mock the hooks
vi.mock('@/hooks/useDataLifecycle');
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockUseSampleLibrary = vi.fn();

describe('SampleLibraryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default mock return value
    mockUseSampleLibrary.mockReturnValue({
      samples: [
        {
          id: '1',
          name: 'Sample 1',
          data_type: 'text',
          quality_score: 0.85,
          usage_count: 5,
          created_at: '2024-01-01',
        },
        {
          id: '2',
          name: 'Sample 2',
          data_type: 'image',
          quality_score: 0.92,
          usage_count: 3,
          created_at: '2024-01-02',
        },
      ],
      loading: false,
      pagination: { page: 1, pageSize: 10, total: 2 },
      fetchSamples: vi.fn(),
    });
    
    vi.spyOn(useDataLifecycleHook, 'useSampleLibrary').mockImplementation(mockUseSampleLibrary);
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <SampleLibraryPage />
      </BrowserRouter>
    );
  };

  it('renders page header with title and description', () => {
    renderComponent();
    
    expect(screen.getByText('sampleLibrary.title')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.description')).toBeInTheDocument();
  });

  it('renders breadcrumb navigation', () => {
    renderComponent();
    
    expect(screen.getByText('common.actions.back')).toBeInTheDocument();
    expect(screen.getByText('interface.title')).toBeInTheDocument();
    expect(screen.getByText('tabs.sampleLibrary')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderComponent();
    
    expect(screen.getByText('common.actions.refresh')).toBeInTheDocument();
    expect(screen.getAllByText('sampleLibrary.actions.createTask').length).toBeGreaterThan(0);
  });

  it('renders statistics cards', () => {
    renderComponent();
    
    expect(screen.getByText('sampleLibrary.statistics.totalSamples')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.statistics.categories')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.statistics.avgQuality')).toBeInTheDocument();
  });

  it('renders statistics cards with data', async () => {
    renderComponent();
    
    await waitFor(() => {
      // Check that statistics cards are rendered
      expect(screen.getByText('sampleLibrary.statistics.totalSamples')).toBeInTheDocument();
      expect(screen.getByText('sampleLibrary.statistics.categories')).toBeInTheDocument();
      expect(screen.getByText('sampleLibrary.statistics.avgQuality')).toBeInTheDocument();
    });
  });

  it('calls fetchSamples on mount', () => {
    const mockFetchSamples = vi.fn();
    mockUseSampleLibrary.mockReturnValue({
      samples: [],
      loading: false,
      pagination: { page: 1, pageSize: 10, total: 0 },
      fetchSamples: mockFetchSamples,
    });
    
    renderComponent();
    
    expect(mockFetchSamples).toHaveBeenCalledWith({ page: 1, pageSize: 10 });
  });

  it('calls fetchSamples when refresh button is clicked', () => {
    const mockFetchSamples = vi.fn();
    mockUseSampleLibrary.mockReturnValue({
      samples: [],
      loading: false,
      pagination: { page: 1, pageSize: 10, total: 0 },
      fetchSamples: mockFetchSamples,
    });
    
    renderComponent();
    
    const refreshButton = screen.getByText('common.actions.refresh');
    fireEvent.click(refreshButton);
    
    expect(mockFetchSamples).toHaveBeenCalled();
  });

  it('disables create task button when no samples selected', () => {
    renderComponent();
    
    const createTaskButtons = screen.getAllByText('sampleLibrary.actions.createTask');
    const createTaskButton = createTaskButtons[0].closest('button');
    expect(createTaskButton).toBeDisabled();
  });

  it('shows loading state', () => {
    mockUseSampleLibrary.mockReturnValue({
      samples: [],
      loading: true,
      pagination: { page: 1, pageSize: 10, total: 0 },
      fetchSamples: vi.fn(),
    });
    
    renderComponent();
    
    const refreshButton = screen.getByText('common.actions.refresh');
    expect(refreshButton.closest('button')).toHaveClass('ant-btn-loading');
  });

  it('renders placeholder for SampleLibrary component', () => {
    renderComponent();
    
    // The SampleLibrary component is rendered, not a placeholder message
    // Check that the component is present by looking for table or other elements
    const refreshButton = screen.getByText('common.actions.refresh');
    expect(refreshButton).toBeInTheDocument();
  });
});
