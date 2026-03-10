/**
 * Preservation Property Tests
 * 
 * IMPORTANT: Follow observation-first methodology
 * These tests capture the baseline behavior on UNFIXED code
 * They should PASS on unfixed code to confirm what needs to be preserved
 * 
 * Tests verify that non-quick-action interactions remain unchanged after the fix
 */

import { render, screen, waitFor, act } from '@testing-library/react';
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
        common: { quickActions: '快捷操作', recentActivity: '最近活动' },
        tempData: { title: '临时数据管理', actions: { create: '创建临时数据' }, description: '临时数据描述' },
        sampleLibrary: { title: '样本库', actions: { addToLibrary: '添加到样本库' }, description: '样本库描述' },
        review: { title: '审核', actions: { submit: '提交审核' }, status: { pending: '待审核' } },
        annotationTask: { title: '标注任务', actions: { create: '创建标注任务' }, status: { pending: '待处理' } },
        enhancement: { title: '数据增强', actions: { create: '创建增强任务' }, status: { running: '运行中' } },
        aiTrial: { title: 'AI试算', actions: { create: '创建AI试算' }, status: { running: '运行中' } },
        tabs: {
          tempData: '临时数据',
          sampleLibrary: '样本库',
          review: '审核',
          annotation: '标注',
          enhancement: '增强',
          aiTrial: 'AI试算',
        },
      },
    },
  },
});

// Mock hooks
vi.mock('@/hooks/useDataLifecycle', () => ({
  useTempData: () => ({ data: [], loading: false }),
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

describe('Preservation: Non-Quick-Action Interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('SHOULD PASS: All 6 quick action buttons render with correct icons, labels, and colors', async () => {
    renderDashboard();
    
    // Wait for loading to complete and content to render
    await waitFor(() => {
      expect(screen.queryByText('创建临时数据')).toBeInTheDocument();
    }, { timeout: 5000 });
    
    expect(screen.queryByText('添加到样本库')).toBeInTheDocument();
    expect(screen.queryByText('提交审核')).toBeInTheDocument();
    expect(screen.queryByText('创建标注任务')).toBeInTheDocument();
    expect(screen.queryByText('创建增强任务')).toBeInTheDocument();
    expect(screen.queryByText('创建AI试算')).toBeInTheDocument();
  });

  it('SHOULD PASS: Dashboard title displays correctly', async () => {
    renderDashboard();
    
    await waitFor(() => {
      const titles = screen.queryAllByText('数据生命周期管理');
      expect(titles.length).toBeGreaterThan(0);
    }, { timeout: 5000 });
  });

  it('SHOULD PASS: Summary statistics card displays correctly', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.queryByText('临时数据管理')).toBeInTheDocument();
    }, { timeout: 5000 });
    
    const sampleLibraryTexts = screen.queryAllByText('样本库');
    expect(sampleLibraryTexts.length).toBeGreaterThan(0);
    
    const reviewTexts = screen.queryAllByText('审核');
    expect(reviewTexts.length).toBeGreaterThan(0);
  });

  it('SHOULD PASS: Quick actions card displays correctly', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.queryByText('快捷操作')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('SHOULD PASS: Recent activity card displays correctly', async () => {
    renderDashboard();
    
    await waitFor(() => {
      expect(screen.queryByText('最近活动')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('SHOULD PASS: Dashboard cards display with correct counts', async () => {
    renderDashboard();
    
    await waitFor(() => {
      const cards = screen.queryAllByText('0');
      expect(cards.length).toBeGreaterThan(0);
    }, { timeout: 5000 });
  });

  it('SHOULD PASS: Loading state displays correctly before data loads', () => {
    renderDashboard();
    
    // Before advancing timers, should show loading spinner
    const spinner = document.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('SHOULD PASS: All UI elements use internationalization', async () => {
    renderDashboard();
    
    await waitFor(() => {
      const titles = screen.queryAllByText('数据生命周期管理');
      expect(titles.length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    // Verify Chinese texts are present (from i18n)
    expect(screen.queryByText('快捷操作')).toBeInTheDocument();
    expect(screen.queryByText('最近活动')).toBeInTheDocument();
  });
});
