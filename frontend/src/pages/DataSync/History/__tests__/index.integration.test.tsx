/**
 * Integration tests for DataSync History page with transfer functionality
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SyncHistory from '../index';
import * as dataLifecycleAPI from '@/api/dataLifecycleAPI';

// Mock the API
vi.mock('@/api/dataLifecycleAPI');

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('DataSync History - Transfer Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
    });
  });

  it('should render sync history page', () => {
    renderWithRouter(<SyncHistory />);
    // Page renders successfully
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('should have row selection enabled', () => {
    renderWithRouter(<SyncHistory />);
    
    // Check that checkboxes exist for row selection
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  it('should display statistics cards', () => {
    renderWithRouter(<SyncHistory />);
    
    // Verify statistics cards are rendered
    const statistics = screen.getAllByRole('img', { name: /check-circle|close-circle/i });
    expect(statistics.length).toBeGreaterThan(0);
  });
});
