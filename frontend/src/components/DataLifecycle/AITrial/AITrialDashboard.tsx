/**
 * AI Trial Dashboard Component
 * 
 * Configure and run AI trial calculations on different data stages.
 * Supports multi-select for comparison and trial execution.
 * 
 * Requirements: 16.3, 16.4, 16.5
 */

import React, { useState } from 'react';
import { Table, Button, Space, Tag, Modal, Card, Statistic, Row, Col } from 'antd';
import {
  PlayCircleOutlined,
  BarChartOutlined,
  SwapOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AITrial } from '@/types/dataLifecycle';
import type { TableRowSelection } from 'antd/es/table/interface';

export interface AITrialDashboardProps {
  trials: AITrial[];
  loading?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
  };
  onCreateTrial?: () => void;
  onExecute?: (trialId: string) => void;
  onViewResults?: (trialId: string) => void;
  onCompare?: (trialIds: string[]) => void;
  onPageChange?: (page: number, pageSize: number) => void;
}

const AITrialDashboard: React.FC<AITrialDashboardProps> = ({
  trials,
  loading = false,
  pagination,
  onCreateTrial,
  onExecute,
  onViewResults,
  onCompare,
  onPageChange,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [selectedTrials, setSelectedTrials] = useState<string[]>([]);
  const [comparisonModalVisible, setComparisonModalVisible] = useState(false);

  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      created: 'default',
      queued: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      cancelled: 'default',
    };
    return colorMap[status] || 'default';
  };

  const handleExecute = (trialId: string) => {
    onExecute?.(trialId);
  };

  const handleViewResults = (trialId: string) => {
    onViewResults?.(trialId);
  };

  const handleCompare = () => {
    if (selectedTrials.length >= 2) {
      setComparisonModalVisible(true);
      onCompare?.(selectedTrials);
    }
  };

  const rowSelection: TableRowSelection<AITrial> = {
    selectedRowKeys: selectedTrials,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedTrials(selectedRowKeys as string[]);
    },
    getCheckboxProps: (record: AITrial) => ({
      disabled: record.status !== 'completed',
    }),
  };

  const columns = [
    {
      title: t('aiTrial.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('aiTrial.columns.dataStage'),
      dataIndex: 'dataStage',
      key: 'dataStage',
      render: (stage: string) => t(`aiTrial.dataStages.${stage}`),
    },
    {
      title: t('aiTrial.columns.aiModel'),
      dataIndex: 'aiModel',
      key: 'aiModel',
    },
    {
      title: t('aiTrial.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {t(`aiTrial.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('aiTrial.columns.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('aiTrial.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: AITrial) => (
        <Space>
          {(record.status === 'created' || record.status === 'queued') && (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
            >
              {t('aiTrial.actions.execute')}
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              type="text"
              icon={<BarChartOutlined />}
              onClick={() => handleViewResults(record.id)}
            >
              {t('aiTrial.actions.viewResults')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const completedTrials = trials.filter(t => t.status === 'completed').length;
  const runningTrials = trials.filter(t => t.status === 'running').length;

  return (
    <div className="ai-trial-dashboard">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('aiTrial.statistics.totalTrials')}
              value={trials.length}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('aiTrial.statistics.completedTrials')}
              value={completedTrials}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('aiTrial.statistics.runningTrials')}
              value={runningTrials}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onCreateTrial}
          >
            {t('aiTrial.createNew')}
          </Button>
          <Button
            icon={<SwapOutlined />}
            disabled={selectedTrials.length < 2}
            onClick={handleCompare}
          >
            {t('aiTrial.compare')}
          </Button>
        </div>

        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={trials}
          rowKey="id"
          loading={loading}
          pagination={
            pagination
              ? {
                  current: pagination.page,
                  pageSize: pagination.pageSize,
                  total: pagination.total,
                  showSizeChanger: true,
                  showTotal: (total) => t('common.pagination.total', { total }),
                  onChange: onPageChange,
                }
              : false
          }
        />
      </Card>

      <Modal
        title={t('aiTrial.comparisonModal.title')}
        open={comparisonModalVisible}
        onCancel={() => setComparisonModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setComparisonModalVisible(false)}>
            {t('common.actions.close')}
          </Button>,
        ]}
        width={800}
      >
        <p>{t('aiTrial.comparisonModal.description')}</p>
        <div>
          {selectedTrials.map(trialId => {
            const trial = trials.find(t => t.id === trialId);
            return trial ? (
              <Card key={trialId} style={{ marginBottom: 8 }}>
                <p><strong>{t('aiTrial.columns.name')}:</strong> {trial.name}</p>
                <p><strong>{t('aiTrial.columns.aiModel')}:</strong> {trial.aiModel}</p>
                <p><strong>{t('aiTrial.columns.dataStage')}:</strong> {t(`aiTrial.dataStages.${trial.dataStage}`)}</p>
              </Card>
            ) : null;
          })}
        </div>
      </Modal>
    </div>
  );
};

export default AITrialDashboard;
