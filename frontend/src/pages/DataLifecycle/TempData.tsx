/**
 * TempData Page Component
 * 
 * Displays temporary data management interface with table, filters, and review modal.
 * Integrates TempDataTable and ReviewModal components.
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Select,
  DatePicker,
  Input,
  Breadcrumb,
  message,
} from 'antd';
import {
  UploadOutlined,
  FilterOutlined,
  ReloadOutlined,
  HomeOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import TempDataTable from '@/components/DataLifecycle/TempData/TempDataTable';
import ReviewModal from '@/components/DataLifecycle/Review/ReviewModal';
import { useTempData, useReview } from '@/hooks/useDataLifecycle';
import type { TempData, Review } from '@/services/dataLifecycle';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ============================================================================
// Types
// ============================================================================

interface FilterState {
  state?: string;
  uploader?: string;
  dateRange?: [string, string];
  search?: string;
}

// ============================================================================
// Component
// ============================================================================

const TempDataPage: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const navigate = useNavigate();
  
  const {
    data,
    loading,
    pagination,
    fetchTempData,
    setFilters,
    clearFilters,
  } = useTempData();
  
  const {
    submitForReview,
  } = useReview();

  const [filters, setLocalFilters] = useState<FilterState>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);

  // Handle filter changes
  const handleFilterChange = useCallback((key: keyof FilterState, value: any) => {
    setLocalFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  // Apply filters
  const handleApplyFilters = useCallback(() => {
    setFilters(filters as Record<string, unknown>);
    fetchTempData({
      page: 1,
      pageSize: pagination.pageSize,
      state: filters.state,
    });
  }, [filters, setFilters, fetchTempData, pagination.pageSize]);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setLocalFilters({});
    clearFilters();
    fetchTempData({ page: 1, pageSize: pagination.pageSize });
  }, [clearFilters, fetchTempData, pagination.pageSize]);

  // Refresh data
  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    fetchTempData({ page: pagination.page, pageSize: pagination.pageSize });
  }, [fetchTempData, pagination.page, pagination.pageSize]);

  // Handle upload document
  const handleUploadDocument = useCallback(() => {
    navigate('/data-structuring/upload');
  }, [navigate]);

  // Handle view details
  const handleViewDetails = useCallback((record: TempData) => {
    // For now, just show a message. In the future, this could open a detail modal
    message.info(t('tempData.messages.viewDetails'));
  }, [t]);

  // Handle edit
  const handleEdit = useCallback((record: TempData) => {
    // For now, just show a message. In the future, this could open an edit modal
    message.info(t('tempData.actions.edit'));
  }, [t]);

  // Handle submit for review
  const handleSubmitForReview = useCallback(async (record: TempData) => {
    try {
      await submitForReview('temp_data', record.id);
      message.success(t('review.messages.submitSuccess'));
      handleRefresh();
    } catch {
      message.error(t('review.messages.submitFailed'));
    }
  }, [submitForReview, t, handleRefresh]);

  // Handle review modal close
  const handleReviewModalClose = useCallback(() => {
    setReviewModalVisible(false);
    setSelectedReview(null);
  }, []);

  // Handle review success
  const handleReviewSuccess = useCallback(() => {
    handleRefresh();
  }, [handleRefresh]);

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Breadcrumb */}
        <Breadcrumb
          items={[
            {
              href: '/',
              title: (
                <Space>
                  <HomeOutlined />
                  <span>{t('common.actions.back')}</span>
                </Space>
              ),
            },
            {
              href: '/data-lifecycle',
              title: (
                <Space>
                  <DatabaseOutlined />
                  <span>{t('interface.title')}</span>
                </Space>
              ),
            },
            {
              title: t('tabs.tempData'),
            },
          ]}
        />

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              {t('tempData.title')}
            </Title>
            <Text type="secondary">{t('tempData.description')}</Text>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
            >
              {t('common.actions.refresh')}
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={handleUploadDocument}
            >
              {t('tempData.uploadDocument')}
            </Button>
          </Space>
        </div>

        {/* Filters */}
        <Card size="small">
          <Space wrap style={{ width: '100%' }}>
            <Select
              placeholder={t('tempData.filters.state')}
              style={{ width: 150 }}
              value={filters.state}
              onChange={(value) => handleFilterChange('state', value)}
              allowClear
            >
              <Select.Option value="draft">{t('tempData.states.draft')}</Select.Option>
              <Select.Option value="processing">{t('tempData.states.processing')}</Select.Option>
              <Select.Option value="ready">{t('tempData.states.ready')}</Select.Option>
              <Select.Option value="archived">{t('tempData.states.archived')}</Select.Option>
            </Select>

            <Input
              placeholder={t('tempData.filters.uploader')}
              style={{ width: 200 }}
              value={filters.uploader}
              onChange={(e) => handleFilterChange('uploader', e.target.value)}
              allowClear
            />

            <RangePicker
              placeholder={[t('tempData.filters.startDate'), t('tempData.filters.endDate')]}
              onChange={(dates, dateStrings) => {
                if (dates && dates[0] && dates[1]) {
                  handleFilterChange('dateRange', dateStrings as [string, string]);
                } else {
                  handleFilterChange('dateRange', undefined);
                }
              }}
            />

            <Button
              type="primary"
              icon={<FilterOutlined />}
              onClick={handleApplyFilters}
            >
              {t('common.actions.filter')}
            </Button>

            <Button onClick={handleClearFilters}>
              {t('common.actions.reset')}
            </Button>
          </Space>
        </Card>

        {/* Data Table */}
        <Card>
          <TempDataTable
            onEdit={handleEdit}
            onView={handleViewDetails}
            refreshKey={refreshKey}
          />
        </Card>

        {/* Statistics */}
        <Card size="small">
          <Space split="|">
            <Text type="secondary">
              {t('common.pagination.total', { total: pagination.total })}
            </Text>
            <Text type="secondary">
              {t('tempData.filters.state')}: {filters.state || t('tempData.filters.all')}
            </Text>
          </Space>
        </Card>
      </Space>

      {/* Review Modal */}
      <ReviewModal
        visible={reviewModalVisible}
        review={selectedReview}
        onClose={handleReviewModalClose}
        onSuccess={handleReviewSuccess}
      />
    </div>
  );
};

export default TempDataPage;
