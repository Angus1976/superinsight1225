import React, { useState } from 'react';
import { Upload, Card, Table, Button, Space, Descriptions, Alert } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { ToolkitPageLayout } from '@/components/DataToolkit';

const { Dragger } = Upload;

interface FileInfo {
  name: string;
  size: number;
  type: string;
}

const MOCK_PREVIEW_COLUMNS = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Value', dataIndex: 'value', key: 'value' },
  { title: 'Category', dataIndex: 'category', key: 'category' },
];

const MOCK_PREVIEW_DATA = [
  { key: '1', id: 1, name: 'Sample A', value: 42.5, category: 'alpha' },
  { key: '2', id: 2, name: 'Sample B', value: 18.3, category: 'beta' },
  { key: '3', id: 3, name: 'Sample C', value: 91.0, category: 'alpha' },
];

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const DataUploadPage: React.FC = () => {
  const { t } = useTranslation('dataToolkit');
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [profileReady, setProfileReady] = useState(false);

  const handleUpload = (file: File) => {
    setFileInfo({ name: file.name, size: file.size, type: file.type || 'unknown' });
    setProfileReady(false);
    return false;
  };

  const handleAnalyze = () => {
    setAnalyzing(true);
    setTimeout(() => {
      setAnalyzing(false);
      setProfileReady(true);
    }, 1500);
  };

  return (
    <ToolkitPageLayout titleKey="upload.title">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Dragger
            beforeUpload={handleUpload}
            showUploadList={false}
            accept=".csv,.json,.xlsx,.xls,.pdf,.txt,.xml"
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">{t('upload.dragText')}</p>
            <p className="ant-upload-hint">{t('upload.supportedFormats')}</p>
          </Dragger>
        </Card>

        {fileInfo && (
          <Card title={t('upload.fileInfo')}>
            <Descriptions column={3} size="small">
              <Descriptions.Item label={t('upload.fileName')}>{fileInfo.name}</Descriptions.Item>
              <Descriptions.Item label={t('upload.fileSize')}>{formatFileSize(fileInfo.size)}</Descriptions.Item>
              <Descriptions.Item label={t('upload.fileType')}>{fileInfo.type}</Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        {fileInfo && (
          <Card title={t('upload.preview')}>
            <Table
              columns={MOCK_PREVIEW_COLUMNS}
              dataSource={MOCK_PREVIEW_DATA}
              pagination={false}
              size="small"
            />
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button type="primary" loading={analyzing} onClick={handleAnalyze}>
                {t('common.next')}
              </Button>
            </div>
          </Card>
        )}

        {profileReady && (
          <Card title={t('strategy.recommended')}>
            <Alert
              type="info"
              message={t('strategy.explanation')}
              description="Streaming processing with PostgreSQL storage is recommended for this tabular dataset."
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Button type="primary">{t('strategy.confirm')}</Button>
          </Card>
        )}
      </Space>
    </ToolkitPageLayout>
  );
};
