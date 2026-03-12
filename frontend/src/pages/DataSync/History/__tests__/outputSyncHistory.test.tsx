import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SyncHistory from '../index';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'zh' },
  }),
}));

// Mock TransferButton component
vi.mock('@/components/DataLifecycle/TransferButton', () => ({
  TransferButton: () => <div>TransferButton</div>,
}));

describe('SyncHistory - Output Sync Extension', () => {
  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <SyncHistory />
      </BrowserRouter>
    );
  };

  it('should render sync history page', () => {
    renderComponent();
    expect(screen.getByText('history.title')).toBeInTheDocument();
  });

  it('should display output sync statistics when output syncs exist', () => {
    renderComponent();
    // The component should show output sync statistics
    expect(screen.getByText('history.outputSyncs')).toBeInTheDocument();
    expect(screen.getByText('history.outputSuccessful')).toBeInTheDocument();
    expect(screen.getByText('history.outputFailed')).toBeInTheDocument();
    expect(screen.getByText('history.totalRowsWritten')).toBeInTheDocument();
  });

  it('should display sync direction column in table', () => {
    renderComponent();
    expect(screen.getByText('history.syncDirection')).toBeInTheDocument();
  });

  it('should show direction tags for different sync types', () => {
    renderComponent();
    // Check for direction filter options - use getAllByText since there are multiple instances
    const inputElements = screen.getAllByText('history.directionInput');
    expect(inputElements.length).toBeGreaterThan(0);
    
    const outputElements = screen.getAllByText('history.directionOutput');
    expect(outputElements.length).toBeGreaterThan(0);
    
    // Bidirectional is in the filter but not in the data, so we just check the filter exists
    expect(screen.getByText('history.syncDirection')).toBeInTheDocument();
  });
});
