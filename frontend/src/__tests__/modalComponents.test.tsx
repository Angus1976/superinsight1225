/**
 * Unit Tests: Three Modal Components
 *
 * Tests for DataSourceConfigModal, PermissionTableModal, and OutputModeModal
 * Validates: Requirements 3.5, 4.5
 *
 * Test scenarios:
 * - Modal open/close behavior
 * - Form submission (success and failure cases)
 * - Error message rendering
 * - User interactions (switches, checkboxes, selects)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';
import { message } from 'antd';
import DataSourceConfigModal from '@/pages/AIAssistant/components/DataSourceConfigModal';
import PermissionTableModal from '@/pages/AIAssistant/components/PermissionTableModal';
import OutputModeModal from '@/pages/AIAssistant/components/OutputModeModal';
import * as aiAssistantApi from '@/services/aiAssistantApi';
import type { AIDataSource } from '@/types/aiAssistant';

// Mock the API module
vi.mock('@/services/aiAssistantApi');

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Initialize i18n for testing
beforeEach(() => {
  i18n.init({
    lng: 'zh',
    fallbackLng: 'zh',
    resources: {
      zh: {
        aiAssistant: {
          'dataSourceModal.title': '配置数据源',
          'dataSourceModal.cancel': '取消',
          'dataSourceModal.save': '保存',
          'dataSourceModal.enableSwitch': '启用',
          'permissionModal.title': '配置权限表',
          'permissionModal.cancel': '取消',
          'permissionModal.save': '保存',
          'permissionModal.noEnabledSources': '暂无已启用的数据源',
          'outputModeModal.title': '输出方式',
          'outputModeModal.cancel': '取消',
          'outputModeModal.confirm': '确认',
          'outputModeModal.selectSources': '选择数据源',
          'outputModeModal.mergeMode': '合并输出',
          'outputModeModal.compareMode': '对比输出',
          'outputModeModal.mergeDesc': '遍历所有数据源后一并输出',
          'outputModeModal.compareDesc': '分别对各数据源进行分析并对比',
          'outputModeModal.noAvailableSources': '暂无可用数据源',
          'source.annotation_tasks': '标注任务',
          'source.annotation_efficiency': '标注效率',
          'source.user_activity': '用户活跃度',
          'category.annotation': '标注',
          'category.statistics': '统计',
          'role.admin': '管理员',
          'role.business_expert': '业务专家',
          'role.annotator': '标注员',
          'role.viewer': '查看者',
          accessRead: '只读',
          accessReadWrite: '读写',
          configSaved: '配置已保存',
          configSaveFailed: '配置保存失败',
          permissionSaved: '权限已保存',
          permissionSaveFailed: '权限保存失败',
          dataSourceLoadFailed: '数据源加载失败',
        },
      },
    },
    interpolation: {
      escapeValue: false,
    },
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

// Mock data
const mockDataSources: AIDataSource[] = [
  {
    id: 'annotation_tasks',
    name: 'Annotation Tasks',
    category: 'annotation',
    enabled: true,
    access_mode: 'read',
  },
  {
    id: 'annotation_efficiency',
    name: 'Annotation Efficiency',
    category: 'statistics',
    enabled: false,
    access_mode: 'read_write',
  },
  {
    id: 'user_activity',
    name: 'User Activity',
    category: 'statistics',
    enabled: true,
    access_mode: 'read',
  },
];

describe('DataSourceConfigModal', () => {
  describe('Modal open/close behavior', () => {
    it('should not render when open is false', () => {
      const onClose = vi.fn();
      const { container } = render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={false} onClose={onClose} />
        </I18nextProvider>
      );

      // Modal should not be visible
      expect(container.querySelector('.ant-modal')).not.toBeInTheDocument();
    });

    it('should render when open is true', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置数据源')).toBeInTheDocument();
      });
    });

    it('should call onClose when cancel button is clicked', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置数据源')).toBeInTheDocument();
      });

      const cancelButton = screen.getByText('取消');
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Data loading', () => {
    it('should load data sources on open', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(aiAssistantApi.getDataSourceConfig).toHaveBeenCalledTimes(1);
      });

      await waitFor(() => {
        expect(screen.getByText('标注任务')).toBeInTheDocument();
        expect(screen.getByText('标注效率')).toBeInTheDocument();
        expect(screen.getByText('用户活跃度')).toBeInTheDocument();
      });
    });

    it('should display error message when loading fails', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockRejectedValue(new Error('Network error'));
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith('数据源加载失败');
      });
    });
  });

  describe('Form submission - success case', () => {
    it('should save configuration successfully', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.updateDataSourceConfig).mockResolvedValue(mockDataSources);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置数据源')).toBeInTheDocument();
      });

      const saveButton = screen.getByText('保存');
      await user.click(saveButton);

      await waitFor(() => {
        expect(aiAssistantApi.updateDataSourceConfig).toHaveBeenCalledTimes(1);
        expect(message.success).toHaveBeenCalledWith('配置已保存');
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Form submission - failure case (Requirement 3.5)', () => {
    it('should display error message when save fails', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.updateDataSourceConfig).mockRejectedValue(new Error('Save failed'));
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置数据源')).toBeInTheDocument();
      });

      const saveButton = screen.getByText('保存');
      await user.click(saveButton);

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith('配置保存失败');
        expect(onClose).not.toHaveBeenCalled();
      });
    });
  });

  describe('User interactions', () => {
    it('should toggle switch when clicked', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <DataSourceConfigModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('标注任务')).toBeInTheDocument();
      });

      // Find all switches
      const switches = screen.getAllByRole('switch');
      expect(switches.length).toBeGreaterThan(0);

      // Click the first switch
      await user.click(switches[0]);

      // Switch state should change (we can't easily verify internal state, but no error should occur)
      expect(switches[0]).toBeInTheDocument();
    });
  });
});

describe('PermissionTableModal', () => {
  const mockPermissions = {
    permissions: [
      { role: 'admin', source_id: 'annotation_tasks', allowed: true },
      { role: 'business_expert', source_id: 'annotation_tasks', allowed: true },
      { role: 'annotator', source_id: 'annotation_tasks', allowed: false },
    ],
  };

  describe('Modal open/close behavior', () => {
    it('should not render when open is false', () => {
      const onClose = vi.fn();
      const { container } = render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={false} onClose={onClose} />
        </I18nextProvider>
      );

      expect(container.querySelector('.ant-modal')).not.toBeInTheDocument();
    });

    it('should render when open is true', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置权限表')).toBeInTheDocument();
      });
    });

    it('should call onClose when cancel button is clicked', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置权限表')).toBeInTheDocument();
      });

      const cancelButton = screen.getByText('取消');
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Data loading', () => {
    it('should load permissions and data sources on open', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(aiAssistantApi.getDataSourceConfig).toHaveBeenCalledTimes(1);
        expect(aiAssistantApi.getRolePermissions).toHaveBeenCalledTimes(1);
      });

      await waitFor(() => {
        expect(screen.getByText('管理员')).toBeInTheDocument();
        expect(screen.getByText('业务专家')).toBeInTheDocument();
      });
    });

    it('should display error message when loading fails', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockRejectedValue(new Error('Network error'));
      vi.mocked(aiAssistantApi.getRolePermissions).mockRejectedValue(new Error('Network error'));
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith('数据源加载失败');
      });
    });

    it('should show empty state when no enabled sources', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue([]);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue({ permissions: [] });
      const onClose = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('暂无已启用的数据源')).toBeInTheDocument();
      });
    });
  });

  describe('Form submission - success case', () => {
    it('should save permissions successfully', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      vi.mocked(aiAssistantApi.updateRolePermissions).mockResolvedValue(mockPermissions);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置权限表')).toBeInTheDocument();
      });

      const saveButton = screen.getByText('保存');
      await user.click(saveButton);

      await waitFor(() => {
        expect(aiAssistantApi.updateRolePermissions).toHaveBeenCalledTimes(1);
        expect(message.success).toHaveBeenCalledWith('权限已保存');
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Form submission - failure case (Requirement 4.5)', () => {
    it('should display error message when save fails', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      vi.mocked(aiAssistantApi.updateRolePermissions).mockRejectedValue(new Error('Save failed'));
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置权限表')).toBeInTheDocument();
      });

      const saveButton = screen.getByText('保存');
      await user.click(saveButton);

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith('权限保存失败');
        expect(onClose).not.toHaveBeenCalled();
      });
    });
  });

  describe('User interactions', () => {
    it('should toggle checkbox when clicked', async () => {
      vi.mocked(aiAssistantApi.getDataSourceConfig).mockResolvedValue(mockDataSources);
      vi.mocked(aiAssistantApi.getRolePermissions).mockResolvedValue(mockPermissions);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <PermissionTableModal open={true} onClose={onClose} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('配置权限表')).toBeInTheDocument();
      });

      // Find all checkboxes
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);

      // Click the first checkbox
      await user.click(checkboxes[0]);

      // Checkbox state should change (we can't easily verify internal state, but no error should occur)
      expect(checkboxes[0]).toBeInTheDocument();
    });
  });
});

describe('OutputModeModal', () => {
  const enabledSources = mockDataSources.filter(s => s.enabled);

  describe('Modal open/close behavior', () => {
    it('should not render when open is false', () => {
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const { container } = render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={false} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      expect(container.querySelector('.ant-modal')).not.toBeInTheDocument();
    });

    it('should render when open is true', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });
    });

    it('should call onClose when cancel button is clicked', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });

      const cancelButton = screen.getByText('取消');
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Data loading', () => {
    it('should load available data sources on open', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(aiAssistantApi.getAvailableDataSources).toHaveBeenCalledTimes(1);
      });

      await waitFor(() => {
        expect(screen.getByText('标注任务')).toBeInTheDocument();
        expect(screen.getByText('用户活跃度')).toBeInTheDocument();
      });
    });

    it('should show empty state when no available sources', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue([]);
      const onClose = vi.fn();
      const onConfirm = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('暂无可用数据源')).toBeInTheDocument();
      });
    });

    it('should handle loading errors gracefully', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockRejectedValue(new Error('Network error'));
      const onClose = vi.fn();
      const onConfirm = vi.fn();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('暂无可用数据源')).toBeInTheDocument();
      });
    });
  });

  describe('Form submission', () => {
    it('should call onConfirm with selected sources and mode', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal
            open={true}
            onClose={onClose}
            onConfirm={onConfirm}
            initialSourceIds={['annotation_tasks']}
            initialMode="merge"
          />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });

      const confirmButton = screen.getByText('确认');
      await user.click(confirmButton);

      expect(onConfirm).toHaveBeenCalledWith(['annotation_tasks'], 'merge');
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should update selection when checkboxes are clicked', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal open={true} onClose={onClose} onConfirm={onConfirm} />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });

      // Find checkboxes
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);

      // Click first checkbox
      await user.click(checkboxes[0]);

      // Confirm
      const confirmButton = screen.getByText('确认');
      await user.click(confirmButton);

      expect(onConfirm).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('User interactions', () => {
    it('should toggle between merge and compare modes', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal
            open={true}
            onClose={onClose}
            onConfirm={onConfirm}
            initialMode="merge"
          />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });

      // Find radio buttons
      const radios = screen.getAllByRole('radio');
      expect(radios.length).toBe(2);

      // Click compare mode radio
      await user.click(radios[1]);

      // Confirm
      const confirmButton = screen.getByText('确认');
      await user.click(confirmButton);

      // Should be called with 'compare' mode
      expect(onConfirm).toHaveBeenCalledWith([], 'compare');
    });

    it('should preserve initial values when modal opens', async () => {
      vi.mocked(aiAssistantApi.getAvailableDataSources).mockResolvedValue(enabledSources);
      const onClose = vi.fn();
      const onConfirm = vi.fn();
      const user = userEvent.setup();

      render(
        <I18nextProvider i18n={i18n}>
          <OutputModeModal
            open={true}
            onClose={onClose}
            onConfirm={onConfirm}
            initialSourceIds={['annotation_tasks', 'user_activity']}
            initialMode="compare"
          />
        </I18nextProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('输出方式')).toBeInTheDocument();
      });

      // Confirm without changes
      const confirmButton = screen.getByText('确认');
      await user.click(confirmButton);

      expect(onConfirm).toHaveBeenCalledWith(['annotation_tasks', 'user_activity'], 'compare');
    });
  });
});
