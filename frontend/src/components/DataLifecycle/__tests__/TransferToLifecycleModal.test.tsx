/**
 * TransferToLifecycleModal Unit Tests
 * 
 * Tests cover:
 * - Modal opening/closing
 * - Form validation
 * - Target stage dynamic display based on sourceType
 * - User interactions (stage selection, input configuration)
 * - Permission levels and approval workflow
 * - Progress tracking and error handling
 * 
 * Validates Requirements: 1.2, 1.3, 2.2, 3.2, 4.2
 */

import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';
import TransferToLifecycleModal, { TransferDataItem } from '../TransferToLifecycleModal';
import { useAuthStore } from '@/stores/authStore';
import { useTransferToLifecycle } from '@/hooks/useTransferToLifecycle';

// Mock dependencies
vi.mock('@/stores/authStore');
vi.mock('@/hooks/useTransferToLifecycle');

// Initialize i18n for testing
i18n.init({
  lng: 'zh',
  fallbackLng: 'zh',
  interpolation: {
    escapeValue: false,
  },
  resources: {
    zh: {
      aiProcessing: {
        transfer: {
          modal: {
            title: '转存数据到数据生命周期',
            selectStage: '选择目标阶段',
            dataType: '数据类型',
            tags: '标签',
            tagsPlaceholder: '输入标签后按回车',
            remark: '备注',
            remarkPlaceholder: '添加备注信息（可选）',
            qualityThreshold: '质量阈值',
            selectedCount: '已选择 {{count}} 条数据',
            preview: '数据预览',
            typeGrouping: '按类型分组',
            annotationInfo: '标注任务信息',
            taskName: '任务名称',
            annotationCount: '标注数据数量',
            qualityDistribution: '质量分布',
            highQuality: '高质量',
            mediumQuality: '中等质量',
            lowQuality: '低质量',
          },
          stages: {
            temp_data: '临时数据',
            sample_library: '样本库',
            annotated: '已标注',
            enhanced: '已增强',
          },
          dataTypes: {
            text: '文本',
            image: '图像',
            audio: '音频',
            video: '视频',
          },
          messages: {
            success: '成功转存 {{count}} 条数据到{{stage}}',
            partialSuccess: '转存完成：成功 {{success}} 条，失败 {{failed}} 条',
            failed: '转存失败：{{reason}}',
            noStageSelected: '请选择目标阶段',
          },
          progress: {
            title: '转存进度',
            processing: '正在处理 {{current}}/{{total}}',
          },
          approval: {
            title: '审批申请',
            submitApproval: '提交审批',
            directTransfer: '直接转存',
            reason: '申请理由',
            reasonPlaceholder: '请说明转存原因',
            status: {
              pending: '待审批',
            },
            messages: {
              submitted: '审批申请已提交，等待审批',
            },
          },
          permission: {
            level: {
              administrator: '管理员',
              approvalRequired: '需要审批',
            },
            yourLevel: '您的权限级别：{{level}}',
          },
        },
      },
      common: {
        action: {
          cancel: '取消',
        },
      },
    },
  },
});

// Test data
const mockSelectedData: TransferDataItem[] = [
  {
    id: '1',
    name: 'Test Data 1',
    content: { text: 'Sample content 1' },
    metadata: { processingMethod: 'structuring' },
  },
  {
    id: '2',
    name: 'Test Data 2',
    content: { text: 'Sample content 2' },
    metadata: { processingMethod: 'structuring' },
  },
];

const mockSemanticData: TransferDataItem[] = [
  {
    id: '1',
    name: 'Entity Record',
    content: { text: 'Entity content', type: 'entity' },
    metadata: { recordType: 'entity' },
  },
  {
    id: '2',
    name: 'Relationship Record',
    content: { text: 'Relationship content', type: 'relationship' },
    metadata: { recordType: 'relationship' },
  },
];

const mockAIAnnotationData: TransferDataItem[] = [
  {
    id: '1',
    name: 'Annotation Task 1',
    content: { annotations: [] },
    metadata: { annotatedCount: 100, averageConfidence: 0.85 },
  },
];

describe('TransferToLifecycleModal', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();
  const mockTransferData = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    (useAuthStore as any).mockReturnValue({
      user: { id: '1', name: 'Test User', role: 'user' },
    });

    (useTransferToLifecycle as any).mockReturnValue({
      transferData: mockTransferData,
      loading: false,
      progress: { total: 0, completed: 0, failed: 0, percentage: 0 },
      error: null,
    });
  });

  const renderModal = (props: Partial<Parameters<typeof TransferToLifecycleModal>[0]> = {}) => {
    const defaultProps = {
      visible: true,
      onClose: mockOnClose,
      onSuccess: mockOnSuccess,
      sourceType: 'structuring' as const,
      selectedData: mockSelectedData,
    };

    return render(
      <I18nextProvider i18n={i18n}>
        <TransferToLifecycleModal {...defaultProps} {...props} />
      </I18nextProvider>
    );
  };

  // ============================================================================
  // Test Suite 1: Modal Opening and Closing
  // ============================================================================

  describe('Modal Opening and Closing', () => {
    it('should render modal when visible is true', () => {
      renderModal({ visible: true });
      expect(screen.getByText('转存数据到数据生命周期')).toBeInTheDocument();
    });

    it('should not render modal when visible is false', () => {
      renderModal({ visible: false });
      expect(screen.queryByText('转存数据到数据生命周期')).not.toBeInTheDocument();
    });

    it('should call onClose when cancel button is clicked', async () => {
      renderModal();
      const cancelButton = screen.getByText('取消');
      fireEvent.click(cancelButton);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should reset form when modal closes', async () => {
      const { rerender } = renderModal({ visible: true });
      
      // Fill in form
      const stageSelect = screen.getByText('选择目标阶段').closest('.ant-form-item')?.querySelector('.ant-select-selector');
      if (stageSelect) {
        fireEvent.mouseDown(stageSelect);
      }
      
      // Close modal
      rerender(
        <I18nextProvider i18n={i18n}>
          <TransferToLifecycleModal
            visible={false}
            onClose={mockOnClose}
            sourceType="structuring"
            selectedData={mockSelectedData}
          />
        </I18nextProvider>
      );
      
      // Reopen modal
      rerender(
        <I18nextProvider i18n={i18n}>
          <TransferToLifecycleModal
            visible={true}
            onClose={mockOnClose}
            sourceType="structuring"
            selectedData={mockSelectedData}
          />
        </I18nextProvider>
      );
      
      // Form should be reset
      expect(screen.getByText('选择目标阶段')).toBeInTheDocument();
    });

    it('should disable close button when transfer is in progress', async () => {
      (useTransferToLifecycle as any).mockReturnValue({
        transferData: mockTransferData,
        loading: false,
        progress: { total: 10, completed: 5, failed: 0, percentage: 50 },
        error: null,
      });

      mockTransferData.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderModal();
      
      // Submit form to start transfer
      const okButton = screen.getByText('直接转存');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        const modal = document.querySelector('.ant-modal');
        expect(modal).toHaveAttribute('closable', 'false');
      });
    });
  });

  // ============================================================================
  // Test Suite 2: Form Validation
  // ============================================================================

  describe('Form Validation', () => {
    it('should show validation error when submitting without selecting target stage', async () => {
      renderModal();
      
      const okButton = screen.getByText('直接转存');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(screen.getByText('请选择目标阶段')).toBeInTheDocument();
      });
      
      expect(mockTransferData).not.toHaveBeenCalled();
    });

    it('should show validation error when approval reason is missing for regular users', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Test User', role: 'user' },
      });

      renderModal();
      
      await waitFor(() => {
        expect(screen.getByText('申请理由')).toBeInTheDocument();
      });
      
      const okButton = screen.getByText('提交审批');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(screen.getByText('请说明转存原因')).toBeInTheDocument();
      });
    });

    it('should accept valid form submission with all required fields', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      mockTransferData.mockResolvedValue({
        success: true,
        successCount: 2,
        failedCount: 0,
        failedItems: [],
      });

      renderModal();
      
      // Select target stage using label
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      const okButton = screen.getByRole('button', { name: /直接转存/ });
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockTransferData).toHaveBeenCalled();
      });
    });

    it('should validate quality threshold is between 0 and 1 for AI annotation', async () => {
      renderModal({ sourceType: 'ai_annotation', selectedData: mockAIAnnotationData });
      
      const qualityInput = screen.getByPlaceholderText('0.7');
      fireEvent.change(qualityInput, { target: { value: '1.5' } });
      
      // HTML5 validation should prevent invalid values
      expect(qualityInput).toHaveAttribute('max', '1');
      expect(qualityInput).toHaveAttribute('min', '0');
    });
  });

  // ============================================================================
  // Test Suite 3: Target Stage Dynamic Display
  // ============================================================================

  describe('Target Stage Dynamic Display Based on Source Type', () => {
    it('should show temp_data and sample_library for structuring', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal({ sourceType: 'structuring' });
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        expect(screen.getByText('临时数据')).toBeInTheDocument();
        expect(screen.getByText('样本库')).toBeInTheDocument();
        expect(screen.queryByText('已标注')).not.toBeInTheDocument();
        expect(screen.queryByText('已增强')).not.toBeInTheDocument();
      });
    });

    it('should show temp_data, sample_library, and enhanced for vectorization', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal({ sourceType: 'vectorization' });
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        expect(screen.getByText('临时数据')).toBeInTheDocument();
        expect(screen.getByText('样本库')).toBeInTheDocument();
        expect(screen.getByText('已增强')).toBeInTheDocument();
        expect(screen.queryByText('已标注')).not.toBeInTheDocument();
      });
    });

    it('should show temp_data, sample_library, and enhanced for semantic', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal({ sourceType: 'semantic' });
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        expect(screen.getByText('临时数据')).toBeInTheDocument();
        expect(screen.getByText('样本库')).toBeInTheDocument();
        expect(screen.getByText('已增强')).toBeInTheDocument();
        expect(screen.queryByText('已标注')).not.toBeInTheDocument();
      });
    });

    it('should show annotated and sample_library for ai_annotation', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal({ sourceType: 'ai_annotation', selectedData: mockAIAnnotationData });
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        expect(screen.getByText('已标注')).toBeInTheDocument();
        expect(screen.getByText('样本库')).toBeInTheDocument();
        expect(screen.queryByText('临时数据')).not.toBeInTheDocument();
        expect(screen.queryByText('已增强')).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Test Suite 4: User Interactions
  // ============================================================================

  describe('User Interactions', () => {
    beforeEach(() => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });
    });

    it('should allow selecting target stage', async () => {
      renderModal();
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      // Verify selection was made
      expect(stageLabel).toBeInTheDocument();
    });

    it('should allow selecting data type', async () => {
      renderModal();
      
      const dataTypeLabel = screen.getByLabelText('数据类型');
      fireEvent.mouseDown(dataTypeLabel);
      
      await waitFor(() => {
        const option = screen.getByText('文本');
        fireEvent.click(option);
      });
      
      expect(dataTypeLabel).toBeInTheDocument();
    });

    it('should allow adding tags', async () => {
      renderModal();
      
      const tagsInput = screen.getByPlaceholderText('输入标签后按回车');
      fireEvent.change(tagsInput, { target: { value: 'test-tag' } });
      fireEvent.keyDown(tagsInput, { key: 'Enter', code: 'Enter' });
      
      await waitFor(() => {
        expect(screen.getByText('test-tag')).toBeInTheDocument();
      });
    });

    it('should allow entering remark', async () => {
      renderModal();
      
      const remarkInput = screen.getByPlaceholderText('添加备注信息（可选）');
      fireEvent.change(remarkInput, { target: { value: 'Test remark' } });
      
      expect(remarkInput).toHaveValue('Test remark');
    });

    it('should allow entering quality threshold for AI annotation', async () => {
      renderModal({ sourceType: 'ai_annotation', selectedData: mockAIAnnotationData });
      
      const qualityInput = screen.getByPlaceholderText('0.7');
      fireEvent.change(qualityInput, { target: { value: '0.8' } });
      
      expect(qualityInput).toHaveValue('0.8');
    });

    it('should display selected data count', () => {
      renderModal({ selectedData: mockSelectedData });
      expect(screen.getByText('已选择 2 条数据')).toBeInTheDocument();
    });

    it('should display data preview', () => {
      renderModal({ selectedData: mockSelectedData });
      expect(screen.getByText('数据预览')).toBeInTheDocument();
      expect(screen.getByText('Test Data 1')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Test Suite 5: Semantic Type Grouping
  // ============================================================================

  describe('Semantic Type Grouping', () => {
    it('should display type grouping for semantic source type', () => {
      renderModal({ sourceType: 'semantic', selectedData: mockSemanticData });
      
      expect(screen.getByText('按类型分组')).toBeInTheDocument();
      expect(screen.getByText('entity: 1')).toBeInTheDocument();
      expect(screen.getByText('relationship: 1')).toBeInTheDocument();
    });

    it('should not display type grouping for non-semantic source types', () => {
      renderModal({ sourceType: 'structuring' });
      
      expect(screen.queryByText('按类型分组')).not.toBeInTheDocument();
    });

    it('should display correct tag colors for different semantic types', () => {
      renderModal({ sourceType: 'semantic', selectedData: mockSemanticData });
      
      const entityTag = screen.getByText('entity: 1').closest('.ant-tag');
      const relationshipTag = screen.getByText('relationship: 1').closest('.ant-tag');
      
      expect(entityTag).toHaveClass('ant-tag-blue');
      expect(relationshipTag).toHaveClass('ant-tag-green');
    });
  });

  // ============================================================================
  // Test Suite 6: AI Annotation Quality Distribution
  // ============================================================================

  describe('AI Annotation Quality Distribution', () => {
    it('should display annotation task info for ai_annotation source type', () => {
      renderModal({ sourceType: 'ai_annotation', selectedData: mockAIAnnotationData });
      
      expect(screen.getByText('标注任务信息')).toBeInTheDocument();
      expect(screen.getByText('任务名称:')).toBeInTheDocument();
      expect(screen.getByText('Annotation Task 1')).toBeInTheDocument();
      expect(screen.getByText('标注数据数量:')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
    });

    it('should display quality distribution for ai_annotation', () => {
      renderModal({ sourceType: 'ai_annotation', selectedData: mockAIAnnotationData });
      
      expect(screen.getByText('质量分布')).toBeInTheDocument();
      expect(screen.getByText('高质量')).toBeInTheDocument();
      expect(screen.getByText('中等质量')).toBeInTheDocument();
      expect(screen.getByText('低质量')).toBeInTheDocument();
    });

    it('should calculate quality distribution based on average confidence', () => {
      const highConfidenceData: TransferDataItem[] = [
        {
          id: '1',
          name: 'High Quality Task',
          content: { annotations: [] },
          metadata: { annotatedCount: 100, averageConfidence: 0.9 },
        },
      ];

      renderModal({ sourceType: 'ai_annotation', selectedData: highConfidenceData });
      
      // For confidence >= 0.8, should show high: 70%, medium: 25%, low: 5%
      const statistics = screen.getAllByText('%');
      expect(statistics.length).toBeGreaterThan(0);
    });

    it('should not display annotation info for non-ai_annotation source types', () => {
      renderModal({ sourceType: 'structuring' });
      
      expect(screen.queryByText('标注任务信息')).not.toBeInTheDocument();
      expect(screen.queryByText('质量分布')).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Test Suite 7: Permission Levels and Approval Workflow
  // ============================================================================

  describe('Permission Levels and Approval Workflow', () => {
    it('should show direct transfer mode for administrator', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal();
      
      await waitFor(() => {
        expect(screen.getByText('您的权限级别：管理员')).toBeInTheDocument();
        expect(screen.getByText('直接转存')).toBeInTheDocument();
        expect(screen.queryByText('申请理由')).not.toBeInTheDocument();
      });
    });

    it('should show approval mode for regular user', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Regular User', role: 'user' },
      });

      renderModal();
      
      await waitFor(() => {
        expect(screen.getByText('您的权限级别：需要审批')).toBeInTheDocument();
        expect(screen.getByText('提交审批')).toBeInTheDocument();
        expect(screen.getByText('申请理由')).toBeInTheDocument();
      });
    });

    it('should execute direct transfer for administrator', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      mockTransferData.mockResolvedValue({
        success: true,
        successCount: 2,
        failedCount: 0,
        failedItems: [],
      });

      renderModal();
      
      // Select target stage
      const stageSelect = screen.getByText('选择目标阶段').closest('.ant-form-item')?.querySelector('.ant-select-selector');
      if (stageSelect) {
        fireEvent.mouseDown(stageSelect);
        await waitFor(() => {
          const option = screen.getByText('临时数据');
          fireEvent.click(option);
        });
      }
      
      const okButton = screen.getByText('直接转存');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockTransferData).toHaveBeenCalledWith(
          expect.objectContaining({
            sourceType: 'structuring',
            data: mockSelectedData,
            targetStage: 'temp_data',
          })
        );
      });
    });

    it('should create approval request for regular user', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Regular User', role: 'user' },
      });

      renderModal();
      
      // Select target stage
      const stageSelect = screen.getByText('选择目标阶段').closest('.ant-form-item')?.querySelector('.ant-select-selector');
      if (stageSelect) {
        fireEvent.mouseDown(stageSelect);
        await waitFor(() => {
          const option = screen.getByText('临时数据');
          fireEvent.click(option);
        });
      }
      
      // Fill approval reason
      const reasonInput = screen.getByPlaceholderText('请说明转存原因');
      fireEvent.change(reasonInput, { target: { value: 'Need to transfer for testing' } });
      
      const okButton = screen.getByText('提交审批');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(screen.getByText('审批申请已提交，等待审批')).toBeInTheDocument();
      });
    });

    it('should display permission badge with correct status', async () => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });

      renderModal();
      
      await waitFor(() => {
        const badge = screen.getByText('直接转存').closest('.ant-badge');
        expect(badge).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Test Suite 8: Progress Tracking
  // ============================================================================

  describe('Progress Tracking', () => {
    it('should display progress bar during transfer', async () => {
      (useTransferToLifecycle as any).mockReturnValue({
        transferData: mockTransferData,
        loading: false,
        progress: { total: 10, completed: 5, failed: 0, percentage: 50 },
        error: null,
      });

      mockTransferData.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderModal();
      
      // Select target stage and submit
      const stageSelect = screen.getByText('选择目标阶段').closest('.ant-form-item')?.querySelector('.ant-select-selector');
      if (stageSelect) {
        fireEvent.mouseDown(stageSelect);
        await waitFor(() => {
          const option = screen.getByText('临时数据');
          fireEvent.click(option);
        });
      }
      
      const okButton = screen.getByText('直接转存');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(screen.getByText('转存进度')).toBeInTheDocument();
        expect(screen.getByText('正在处理 5/10')).toBeInTheDocument();
      });
    });

    it('should update progress percentage correctly', async () => {
      (useTransferToLifecycle as any).mockReturnValue({
        transferData: mockTransferData,
        loading: false,
        progress: { total: 100, completed: 75, failed: 0, percentage: 75 },
        error: null,
      });

      mockTransferData.mockImplementation(() => new Promise(() => {}));

      renderModal();
      
      const stageSelect = screen.getByText('选择目标阶段').closest('.ant-form-item')?.querySelector('.ant-select-selector');
      if (stageSelect) {
        fireEvent.mouseDown(stageSelect);
        await waitFor(() => {
          const option = screen.getByText('临时数据');
          fireEvent.click(option);
        });
      }
      
      const okButton = screen.getByText('直接转存');
      fireEvent.click(okButton);
      
      await waitFor(() => {
        const progressBar = document.querySelector('.ant-progress-text');
        expect(progressBar?.textContent).toContain('75/100');
      });
    });

    it('should not display progress bar when not transferring', () => {
      renderModal();
      expect(screen.queryByText('转存进度')).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Test Suite 9: Success and Error Handling
  // ============================================================================

  describe('Success and Error Handling', () => {
    beforeEach(() => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });
    });

    it('should display success message on successful transfer', async () => {
      mockTransferData.mockResolvedValue({
        success: true,
        successCount: 2,
        failedCount: 0,
        failedItems: [],
      });

      renderModal();
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      const okButton = screen.getByRole('button', { name: /直接转存/ });
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('should display partial success message when some items fail', async () => {
      mockTransferData.mockResolvedValue({
        success: false,
        successCount: 1,
        failedCount: 1,
        failedItems: [{ id: '2', reason: 'Network error' }],
      });

      renderModal();
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      const okButton = screen.getByRole('button', { name: /直接转存/ });
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('should display error message on complete failure', async () => {
      mockTransferData.mockResolvedValue({
        success: false,
        successCount: 0,
        failedCount: 2,
        failedItems: [
          { id: '1', reason: 'Network error' },
          { id: '2', reason: 'Permission denied' },
        ],
      });

      renderModal();
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      const okButton = screen.getByRole('button', { name: /直接转存/ });
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockOnClose).not.toHaveBeenCalled();
      });
    });

    it('should handle transfer exception gracefully', async () => {
      mockTransferData.mockRejectedValue(new Error('Network connection failed'));

      renderModal();
      
      const stageLabel = screen.getByLabelText('选择目标阶段');
      fireEvent.mouseDown(stageLabel);
      
      await waitFor(() => {
        const option = screen.getByText('临时数据');
        fireEvent.click(option);
      });
      
      const okButton = screen.getByRole('button', { name: /直接转存/ });
      fireEvent.click(okButton);
      
      await waitFor(() => {
        expect(mockOnClose).not.toHaveBeenCalled();
      });
    });
  });

  // ============================================================================
  // Test Suite 10: Internationalization
  // ============================================================================

  describe('Internationalization', () => {
    beforeEach(() => {
      (useAuthStore as any).mockReturnValue({
        user: { id: '1', name: 'Admin User', role: 'admin' },
      });
    });

    it('should display all text in Chinese', () => {
      renderModal();
      
      // Check for key UI elements
      expect(screen.getByLabelText('选择目标阶段')).toBeInTheDocument();
      expect(screen.getByLabelText('数据类型')).toBeInTheDocument();
      expect(screen.getByLabelText('标签')).toBeInTheDocument();
      expect(screen.getByLabelText('备注')).toBeInTheDocument();
      expect(screen.getByText('已选择 2 条数据')).toBeInTheDocument();
    });

    it('should use translation keys for all user-visible text', () => {
      renderModal();
      
      // Verify that translation function is being used
      expect(screen.getByRole('button', { name: /取消/ })).toBeInTheDocument();
    });
  });
});
