/**
 * SampleDetailDrawer Component Tests
 * 
 * Tests for the sample detail drawer component.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import SampleDetailDrawer from '../SampleDetailDrawer';
import { dataLifecycleApi } from '@/services/dataLifecycle';

// Mock the dataLifecycle API
vi.mock('@/services/dataLifecycle', () => ({
  dataLifecycleApi: {
    getSample: vi.fn(),
  },
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('SampleDetailDrawer', () => {
  const mockSample = {
    id: 'sample-123',
    name: 'Test Sample',
    description: 'Test Description',
    data_type: 'text',
    quality_score: 0.85,
    usage_count: 5,
    created_by: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    metadata: {
      state: 'in_sample_library',
      tags: ['test', 'sample'],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders drawer when open', () => {
    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('tempData.actions.viewDetails')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const { container } = render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={false}
        onClose={vi.fn()}
      />
    );

    // Drawer should not be visible
    expect(container.querySelector('.ant-drawer-open')).not.toBeInTheDocument();
  });

  it('fetches sample details when opened', async () => {
    vi.mocked(dataLifecycleApi.getSample).mockResolvedValue(mockSample);

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(dataLifecycleApi.getSample).toHaveBeenCalledWith('sample-123');
    });
  });

  it('displays loading state while fetching', () => {
    vi.mocked(dataLifecycleApi.getSample).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
      />
    );

    // Check for the Spin component instead of the text
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
  });

  it('displays error when fetch fails', async () => {
    vi.mocked(dataLifecycleApi.getSample).mockRejectedValue(
      new Error('Failed to fetch')
    );

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('common.status.error')).toBeInTheDocument();
    });
  });

  it('calls onClose when drawer is closed', () => {
    const onClose = vi.fn();

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={onClose}
      />
    );

    const closeButton = screen.getByLabelText('Close');
    closeButton.click();

    expect(onClose).toHaveBeenCalled();
  });

  it('calls onEdit when edit button is clicked', async () => {
    vi.mocked(dataLifecycleApi.getSample).mockResolvedValue(mockSample);
    const onEdit = vi.fn();

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
        onEdit={onEdit}
      />
    );

    await waitFor(() => {
      expect(dataLifecycleApi.getSample).toHaveBeenCalled();
    });

    const editButton = screen.getByText('common.actions.edit');
    editButton.click();

    expect(onEdit).toHaveBeenCalledWith('sample-123');
  });

  it('calls onAddToTask when add to task button is clicked', async () => {
    vi.mocked(dataLifecycleApi.getSample).mockResolvedValue(mockSample);
    const onAddToTask = vi.fn();

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
        onAddToTask={onAddToTask}
      />
    );

    await waitFor(() => {
      expect(dataLifecycleApi.getSample).toHaveBeenCalled();
    });

    const addButton = screen.getByText('sampleLibrary.actions.addToTask');
    addButton.click();

    expect(onAddToTask).toHaveBeenCalledWith('sample-123');
  });

  it('renders all tabs', async () => {
    vi.mocked(dataLifecycleApi.getSample).mockResolvedValue(mockSample);

    render(
      <SampleDetailDrawer
        sampleId="sample-123"
        open={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(dataLifecycleApi.getSample).toHaveBeenCalled();
    });

    expect(screen.getByText('sampleLibrary.tabs.overview')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.tabs.content')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.tabs.versions')).toBeInTheDocument();
    expect(screen.getByText('sampleLibrary.tabs.usage')).toBeInTheDocument();
  });
});
