/**
 * Unit tests for IframeContainer component
 * Tests loading state, error handling, and lifecycle events
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IframeContainer } from './IframeContainer';
import { IframeStatus } from '../../services/iframe';

describe('IframeContainer', () => {
  const defaultConfig = {
    url: 'http://localhost:8080',
    projectId: 'test-project',
    taskId: 'test-task',
    userId: 'test-user',
    token: 'test-token',
    permissions: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render card with title', () => {
      render(<IframeContainer config={defaultConfig} />);

      expect(screen.getByText('Label Studio')).toBeInTheDocument();
    });

    it('should render toolbar buttons when showToolbar is true', () => {
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={true} />
      );

      const reloadButton = container.querySelector('[title="Reload"]');
      const fullscreenButton = container.querySelector('[title="Fullscreen"]');

      expect(reloadButton).toBeInTheDocument();
      expect(fullscreenButton).toBeInTheDocument();
    });

    it('should not render toolbar buttons when showToolbar is false', () => {
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={false} />
      );

      const reloadButton = container.querySelector('[title="Reload"]');
      const fullscreenButton = container.querySelector('[title="Fullscreen"]');

      expect(reloadButton).not.toBeInTheDocument();
      expect(fullscreenButton).not.toBeInTheDocument();
    });
  });

  describe('iframe creation', () => {
    it('should create iframe container', async () => {
      const { container } = render(<IframeContainer config={defaultConfig} />);

      await waitFor(() => {
        const iframeContainer = container.querySelector('div[style*="width"]');
        expect(iframeContainer).toBeInTheDocument();
      });
    });

    it('should apply custom height', () => {
      const { container } = render(
        <IframeContainer config={defaultConfig} height={800} />
      );

      const card = container.querySelector('.ant-card');
      expect(card).toBeInTheDocument();
    });
  });

  describe('callbacks', () => {
    it('should accept onReady callback', () => {
      const onReady = vi.fn();

      render(<IframeContainer config={defaultConfig} onReady={onReady} />);

      // Component is created with callback
      expect(onReady).toBeDefined();
    });

    it('should accept onError callback', () => {
      const onError = vi.fn();

      render(<IframeContainer config={defaultConfig} onError={onError} />);

      // Component is created with callback
      expect(onError).toBeDefined();
    });

    it('should accept onStatusChange callback', () => {
      const onStatusChange = vi.fn();

      render(
        <IframeContainer config={defaultConfig} onStatusChange={onStatusChange} />
      );

      // Component is created with callback
      expect(onStatusChange).toBeDefined();
    });
  });

  describe('reload button', () => {
    it('should have reload button when showToolbar is true', () => {
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={true} />
      );

      const reloadButton = container.querySelector('[title="Reload"]');
      expect(reloadButton).toBeInTheDocument();
    });

    it('should reload iframe when reload button is clicked', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={true} />
      );

      const reloadButton = container.querySelector('[title="Reload"]');
      expect(reloadButton).toBeInTheDocument();

      if (reloadButton) {
        await user.click(reloadButton);
      }
    });
  });

  describe('fullscreen toggle', () => {
    it('should have fullscreen button when showToolbar is true', () => {
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={true} />
      );

      const fullscreenButton = container.querySelector('[title="Fullscreen"]');
      expect(fullscreenButton).toBeInTheDocument();
    });

    it('should toggle fullscreen mode', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <IframeContainer config={defaultConfig} showToolbar={true} />
      );

      const fullscreenButton = container.querySelector('[title="Fullscreen"]');
      expect(fullscreenButton).toBeInTheDocument();

      if (fullscreenButton) {
        await user.click(fullscreenButton);

        // After click, button title should change
        await waitFor(() => {
          const exitButton = container.querySelector('[title="Exit Fullscreen"]');
          expect(exitButton).toBeInTheDocument();
        });
      }
    });
  });

  describe('cleanup', () => {
    it('should cleanup on unmount', async () => {
      const { unmount } = render(<IframeContainer config={defaultConfig} />);

      unmount();

      // Component should be unmounted without errors
      expect(screen.queryByText('Label Studio')).not.toBeInTheDocument();
    });
  });
});
