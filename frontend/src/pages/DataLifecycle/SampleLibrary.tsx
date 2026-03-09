/**
 * SampleLibrary Page Component
 * 
 * Displays sample library management interface with search filters, statistics, and table.
 * Allows users to browse samples and create annotation tasks from selected samples.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Breadcrumb,
  Row,
  Col,
  Statistic,
  Modal,
  message,
} from 'antd';
import {
  HomeOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useSampleLibrary } from '@/hooks/useDataLifecycle';
import SampleLibrary from '@/components/DataLifecycle/SampleLibrary';
import SampleDetailDrawer from '@/components/DataLifecycle/SampleLibrary/SampleDetailDrawer';
import type { SearchFilters as ISearchFilters } from '@/components/DataLifecycle/SampleLibrary/SearchFilters';

const { Title, Text } = Typography;

// ============================================================================
// Types
// ============================================================================

interface StatisticsData {
  totalSamples: number;
  samplesByCategory: Record<string, number>;
  averageQualityScore: number;
}

// ============================================================================
// Component
// ============================================================================

const SampleLibraryPage: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const navigate = useNavigate();
  
  const {
    samples,
    loading,
    pagination,
    fetchSamples,
    removeFromLibrary,
  } = useSampleLibrary();

  const [selectedSamples, setSelectedSamples] = useState<string[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null);
  const [statistics, setStatistics] = useState<StatisticsData>({
    totalSamples: 0,
    samplesByCategory: {},
    averageQualityScore: 0,
  });

  // Fetch samples on mount
  useEffect(() => {
    fetchSamples({ page: 1, pageSize: 10 });
  }, [refreshKey]);

  // Calculate statistics when samples change
  useEffect(() => {
    if (samples.length > 0) {
      const categoryCount: Record<string, number> = {};
      let totalQuality = 0;

      samples.forEach(sample => {
        // Count by category
        const category = sample.data_type || 'unknown';
        categoryCount[category] = (categoryCount[category] || 0) + 1;

        // Sum quality scores
        totalQuality += sample.quality_score || 0;
      });

      setStatistics({
        totalSamples: pagination.total,
        samplesByCategory: categoryCount,
        averageQualityScore: samples.length > 0 ? totalQuality / samples.length : 0,
      });
    }
  }, [samples, pagination.total]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    fetchSamples({ page: pagination.page, pageSize: pagination.pageSize });
  }, [fetchSamples, pagination.page, pagination.pageSize]);

  // Handle create task from selected samples
  const handleCreateTask = useCallback(() => {
    if (selectedSamples.length === 0) {
      return;
    }
    // Navigate to annotation tasks page with selected samples
    navigate('/data-lifecycle/annotation-tasks', {
      state: { selectedSamples },
    });
  }, [selectedSamples, navigate]);

  // Handle view sample details
  const handleViewDetails = useCallback((id: string) => {
    setSelectedSampleId(id);
    setDetailDrawerOpen(true);
  }, []);

  // Handle close detail drawer
  const handleCloseDetailDrawer = useCallback(() => {
    setDetailDrawerOpen(false);
    setSelectedSampleId(null);
  }, []);

  // Handle edit sample tags
  const handleEditTags = useCallback((id: string) => {
    // TODO: Implement edit tags modal
    message.info(t('common.actions.edit'));
  }, [t]);

  // Handle add sample to task
  const handleAddToTask = useCallback((id: string) => {
    // Add the sample to selected samples and navigate to create task
    navigate('/data-lifecycle/annotation-tasks', {
      state: { selectedSamples: [id] },
    });
  }, [navigate]);

  // Handle delete sample
  const handleDelete = useCallback(async (id: string) => {
    try {
      await removeFromLibrary(id);
      // Refresh the list after deletion
      fetchSamples({ page: pagination.page, pageSize: pagination.pageSize });
    } catch (error) {
      // Error is already handled by the hook
    }
  }, [removeFromLibrary, fetchSamples, pagination.page, pagination.pageSize]);

  // Handle search/filter
  const handleSearch = useCallback((filters: ISearchFilters) => {
    // Convert filters to API parameters
    const params: any = {
      page: 1,
      pageSize: pagination.pageSize,
    };

    if (filters.category) {
      params.dataType = filters.category;
    }

    // TODO: Add support for other filters when backend API supports them
    // - tags
    // - qualityScoreMin/Max
    // - dateFrom/To

    fetchSamples(params);
  }, [fetchSamples, pagination.pageSize]);

  // Handle pagination change
  const handlePageChange = useCallback((page: number, pageSize: number) => {
    fetchSamples({ page, pageSize });
  }, [fetchSamples]);

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
              title: t('tabs.sampleLibrary'),
            },
          ]}
        />

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              {t('sampleLibrary.title')}
            </Title>
            <Text type="secondary">{t('sampleLibrary.description')}</Text>
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
              icon={<PlusOutlined />}
              onClick={handleCreateTask}
              disabled={selectedSamples.length === 0}
            >
              {t('sampleLibrary.actions.createTask')}
            </Button>
          </Space>
        </div>

        {/* Statistics Cards */}
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('sampleLibrary.statistics.totalSamples')}
                value={statistics.totalSamples}
                loading={loading}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('sampleLibrary.statistics.categories')}
                value={Object.keys(statistics.samplesByCategory).length}
                loading={loading}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('sampleLibrary.statistics.avgQuality')}
                value={statistics.averageQualityScore}
                precision={2}
                loading={loading}
              />
            </Card>
          </Col>
        </Row>

        {/* Sample Library Component - Placeholder for task 25.2 */}
        <SampleLibrary
          samples={samples}
          loading={loading}
          pagination={pagination}
          selectedSamples={selectedSamples}
          onSelectionChange={setSelectedSamples}
          onCreateTask={handleCreateTask}
          onViewDetails={handleViewDetails}
          onEditTags={handleEditTags}
          onDelete={handleDelete}
          onSearch={handleSearch}
          onPageChange={handlePageChange}
        />

        {/* Summary */}
        <Card size="small">
          <Space split="|">
            <Text type="secondary">
              {t('common.pagination.total', { total: pagination.total })}
            </Text>
            <Text type="secondary">
              {t('sampleLibrary.statistics.selected', { count: selectedSamples.length })}
            </Text>
          </Space>
        </Card>
      </Space>

      {/* Sample Detail Drawer */}
      <SampleDetailDrawer
        sampleId={selectedSampleId}
        open={detailDrawerOpen}
        onClose={handleCloseDetailDrawer}
        onEdit={handleEditTags}
        onAddToTask={handleAddToTask}
        onDelete={handleDelete}
      />
    </div>
  );
};

export default SampleLibraryPage;
