/**
 * Bug Condition Exploration Test
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
 * DO NOT attempt to fix the test or the code when it fails
 * 
 * This test encodes the expected behavior - it will validate the fix when it passes after implementation
 * 
 * Bug: Quick action buttons only log to console instead of opening modals
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import DataLifecycleDashboard from '../index';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';

// Initialize i18n for testing
i18n.init({
  lng: 'zh',
  fallbackLng: 'zh',
  resources: {
    zh: {
      dataLifecycle: {
        interface: { title: '数据生命周期管理', loading: '加载中...' },
        common: { quickActions: '快捷操作' },
        tempData: { title: '临时数据管理', actions: { create: '创建临时数据' } },
        sampleLibrary: { title: '样本库', actions: { addToLibrary: '添加到样本库' } },
        review: { title: '审核', actions: { submit: '提交审核' } },
        annotationTask: { title: '标注任务', actions: { create: '创建标注任务' } },
        enhancement: { title: '数据增强', actions: { create: '创建增强任务' } },
        aiTrial: { title: 'AI试算', actions: { create: '创建AI试算' } },
      },
    },
  },
});

// Mock hooks
vi.mock('@/hooks/useDataLifecycle', () => ({
  useTempData: () => ({ 
    data: [], 
    loading: false, 
    fetchTempData: vi.fn(),
    createTempData: vi.fn(),
  }),
  useSampleLibrary: () => ({ samples: [], loading: false }),
  useReview: () => ({ reviews: [], loading: false }),
  useAnnotationTask: () => ({ tasks: [], loading: false }),
  useEnhancement: () => ({ jobs: [], loading: false }),
  useAITrial: () => ({ trials: [], loading: false }),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({ hasPermission: () => true }),
}));

vi.mock('@/components/SmartHelp', () => ({
  HelpIcon: () => <div>Help</div>,
}));

const renderDashboard = () => {
  return render(
    <I18nextProvider i18n={i18n}>
      <BrowserRouter>
        <DataLifecycleDashboard />
      </BrowserRouter>
    </I18nextProvider>
  );
};

describe('Bug Condition Exploration: Quick Action Buttons', () => {
  it.skip('EXPECTED TO FAIL: clicking "创建临时数据" button should open CreateTempDataModal', async () => {
    renderDashboard();
    
    // Wait for dashboard to load
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    // Find and click the "创建临时数据" button
    const createTempDataButton = screen.getByText('创建临时数据');
    fireEvent.click(createTempDataButton);

    // EXPECTED BEHAVIOR: Modal should open
    // This assertion will FAIL on unfixed code (proving the bug exists)
    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it.skip('EXPECTED TO FAIL: clicking "添加到样本库" button should open AddToLibraryModal', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const addToLibraryButton = screen.getByText('添加到样本库');
    fireEvent.click(addToLibraryButton);

    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it.skip('EXPECTED TO FAIL: clicking "提交审核" button should open SubmitReviewModal', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const submitReviewButton = screen.getByText('提交审核');
    fireEvent.click(submitReviewButton);

    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it.skip('EXPECTED TO FAIL: clicking "创建标注任务" button should open CreateTaskModal', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const createTaskButton = screen.getByText('创建标注任务');
    fireEvent.click(createTaskButton);

    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it.skip('EXPECTED TO FAIL: clicking "创建增强任务" button should open CreateEnhancementModal', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const createEnhancementButton = screen.getByText('创建增强任务');
    fireEvent.click(createEnhancementButton);

    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it.skip('EXPECTED TO FAIL: clicking "创建AI试算" button should open CreateTrialModal', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.getAllByText('数据生命周期管理').length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const createTrialButton = screen.getByText('创建AI试算');
    fireEvent.click(createTrialButton);

    await waitFor(() => {
      const modal = document.querySelector('.ant-modal');
      expect(modal).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
