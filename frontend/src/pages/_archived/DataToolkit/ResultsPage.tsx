import React, { useCallback } from 'react';
import { Card, Table, Button, Space, Descriptions, Dropdown, Tag } from 'antd';
import { DownloadOutlined, NodeIndexOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { ToolkitPageLayout } from '@/components/DataToolkit';

const MOCK_COLUMNS = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Value', dataIndex: 'value', key: 'value' },
  { title: 'Category', dataIndex: 'category', key: 'category' },
  { title: 'Score', dataIndex: 'score', key: 'score' },
];

const MOCK_DATA = [
  { key: '1', id: 1, name: 'Processed A', value: 42.5, category: 'alpha', score: 0.95 },
  { key: '2', id: 2, name: 'Processed B', value: 18.3, category: 'beta', score: 0.87 },
  { key: '3', id: 3, name: 'Processed C', value: 91.0, category: 'alpha', score: 0.92 },
  { key: '4', id: 4, name: 'Processed D', value: 55.7, category: 'gamma', score: 0.78 },
];

export const ResultsPage: React.FC = () => {
  const { t } = useTranslation('dataToolkit');

  const handleExport = useCallback((format: string) => {
    // Placeholder — actual export logic in Task 9.1
    console.log(`Export as ${format}`);
  }, []);

  const exportMenuItems = [
    { key: 'csv', label: t('results.exportCSV'), onClick: () => handleExport('csv') },
    { key: 'json', label: t('results.exportJSON'), onClick: () => handleExport('json') },
    { key: 'excel', label: t('results.exportExcel'), onClick: () => handleExport('excel') },
    { key: 'pdf', label: t('results.exportPDF'), onClick: () => handleExport('pdf') },
  ];

  return (
    <ToolkitPageLayout
      titleKey="results.title"
      extra={
        <Dropdown menu={{ items: exportMenuItems }}>
          <Button icon={<DownloadOutlined />}>{t('results.export')}</Button>
        </Dropdown>
      }
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title={t('results.summary')}>
          <Descriptions column={3} size="small">
            <Descriptions.Item label={t('results.totalRecords')}>4</Descriptions.Item>
            <Descriptions.Item label={t('results.storageType')}>
              <Tag color="blue">PostgreSQL</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('results.processingTime')}>45s</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title={t('results.visualization')}>
          <Table
            columns={MOCK_COLUMNS}
            dataSource={MOCK_DATA}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>

        <Card title={t('results.lineage')}>
          <Space>
            <NodeIndexOutlined />
            <span>Upload → Parse → Clean → Transform → PostgreSQL</span>
          </Space>
        </Card>
      </Space>
    </ToolkitPageLayout>
  );
};
