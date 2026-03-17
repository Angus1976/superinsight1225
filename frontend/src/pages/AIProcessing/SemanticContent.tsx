/**
 * SemanticContent — 语义化子 Tab
 *
 * Provides file upload, job list table, and semantic record viewing
 * with record_type filtering for the semantic pipeline.
 */

import React, { useEffect, useCallback, useState } from 'react';
import {
  Card,
  Upload,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Alert,
  Select,
} from 'antd';
import {
  InboxOutlined,
  ReloadOutlined,
  EyeOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useSemanticStore } from '@/stores/semanticStore';
import type { SemanticJob, SemanticRecord, SemanticRecordType } from '@/stores/semanticStore';
import TransferToLifecycleModal from '@/components/DataLifecycle/TransferToLifecycleModal';
import type { TransferDataItem } from '@/components/DataLifecycle/TransferToLifecycleModal';
import type { ColumnsType } from 'antd/es/table';
import ProcessingPanel from './components/ProcessingPanel';

const { Dragger } = Upload;
const { Text } = Typography;

const ACCEPTED_EXTENSIONS = [
  '.pdf', '.csv', '.xlsx', '.xls', '.docx', '.html', '.htm', '.txt', '.md', '.json',
  '.pptx', '.ppt', '.mp4', '.avi', '.mov', '.mkv', '.webm',
  '.mp3', '.wav', '.flac', '.ogg', '.m4a',
];

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  extracting: 'processing',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
};

const RECORD_TYPE_COLOR: Record<string, string> = {
  entity: 'blue',
  relationship: 'green',
  summary: 'orange',
};

const SemanticContent: React.FC = () => {
  const { t } = useTranslation(['common', 'aiProcessing']);
  const {
    jobs, records, recordPagination,
    isUploading, isLoadingJobs, isLoadingRecords, error,
    uploadFile, fetchJobs, fetchRecords, clearError,
  } = useSemanticStore();

  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [recordTypeFilter, setRecordTypeFilter] = useState<SemanticRecordType | undefined>(undefined);
  const [selectedRecordKeys, setSelectedRecordKeys] = useState<React.Key[]>([]);
  const [transferModalVisible, setTransferModalVisible] = useState(false);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const handleUpload = useCallback(async (file: File) => {
    try {
      await uploadFile(file);
      message.success(t('common:aiProcessing.uploadSuccess', { defaultValue: '文件上传成功' }));
      fetchJobs();
    } catch {
      message.error(t('common:aiProcessing.uploadFailed', { defaultValue: '文件上传失败' }));
    }
    return false;
  }, [uploadFile, fetchJobs, t]);

  const handleViewRecords = useCallback((jobId: string) => {
    setSelectedJobId(jobId);
    setRecordModalOpen(true);
    setRecordTypeFilter(undefined);
    fetchRecords(jobId);
  }, [fetchRecords]);

  const handleRecordTypeChange = useCallback((value: SemanticRecordType | undefined) => {
    setRecordTypeFilter(value);
    if (selectedJobId) fetchRecords(selectedJobId, 1, 20, value);
  }, [selectedJobId, fetchRecords]);

  const handleRecordPageChange = useCallback((page: number, pageSize: number) => {
    if (selectedJobId) fetchRecords(selectedJobId, page, pageSize, recordTypeFilter);
  }, [selectedJobId, recordTypeFilter, fetchRecords]);

  const handleOpenTransferModal = useCallback(() => {
    if (selectedRecordKeys.length === 0) {
      message.warning(t('aiProcessing:transfer.messages.noDataSelected'));
      return;
    }
    setTransferModalVisible(true);
  }, [selectedRecordKeys, t]);

  const handleTransferSuccess = useCallback(() => {
    setTransferModalVisible(false);
    setSelectedRecordKeys([]);
    message.success(t('aiProcessing:transfer.messages.success', { 
      count: selectedRecordKeys.length,
      stage: t('aiProcessing:transfer.stages.temp_data')
    }));
  }, [selectedRecordKeys, t]);

  const getSelectedRecordsData = useCallback((): TransferDataItem[] => {
    return records
      .filter(record => selectedRecordKeys.includes(record.id))
      .map(record => ({
        id: record.id,
        name: `${record.record_type}-${record.id.substring(0, 8)}`,
        content: {
          text: JSON.stringify(record.content),
          recordType: record.record_type,
          ...record.content,
        },
        metadata: {
          recordType: record.record_type,
          confidence: record.confidence,
          createdAt: record.created_at,
        },
      }));
  }, [records, selectedRecordKeys]);

  const jobColumns: ColumnsType<SemanticJob> = [
    {
      title: t('common:aiProcessing.columns.fileName', { defaultValue: '文件名' }),
      dataIndex: 'file_name',
      ellipsis: true,
    },
    {
      title: t('common:aiProcessing.columns.fileType', { defaultValue: '类型' }),
      dataIndex: 'file_type',
      width: 80,
    },
    {
      title: t('common:aiProcessing.columns.status', { defaultValue: '状态' }),
      dataIndex: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLOR[status] ?? 'default'}>{status}</Tag>
      ),
    },
    {
      title: t('common:aiProcessing.columns.createdAt', { defaultValue: '创建时间' }),
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: t('common:aiProcessing.columns.actions', { defaultValue: '操作' }),
      width: 100,
      render: (_: unknown, record: SemanticJob) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          disabled={record.status !== 'completed'}
          onClick={() => handleViewRecords(record.job_id)}
        >
          {t('common:aiProcessing.viewRecords', { defaultValue: '查看' })}
        </Button>
      ),
    },
  ];

  const recordColumns: ColumnsType<SemanticRecord> = [
    {
      title: t('common:aiProcessing.columns.recordType', { defaultValue: '类型' }),
      dataIndex: 'record_type',
      width: 100,
      render: (type: string) => (
        <Tag color={RECORD_TYPE_COLOR[type] ?? 'default'}>{type}</Tag>
      ),
    },
    {
      title: t('common:aiProcessing.columns.content', { defaultValue: '内容' }),
      dataIndex: 'content',
      ellipsis: true,
      render: (content: Record<string, unknown>) => (
        <Text ellipsis style={{ maxWidth: 400 }}>
          {JSON.stringify(content)}
        </Text>
      ),
    },
    {
      title: t('common:aiProcessing.columns.confidence', { defaultValue: '置信度' }),
      dataIndex: 'confidence',
      width: 90,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
  ];

  const rowSelection = {
    selectedRowKeys: selectedRecordKeys,
    onChange: (selectedKeys: React.Key[]) => {
      setSelectedRecordKeys(selectedKeys);
    },
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {error && (
        <Alert type="error" message={error} closable onClose={clearError} />
      )}

      <Card size="small" title={t('common:aiProcessing.semantic.uploadTitle', { defaultValue: '上传文件' })}>
        <Dragger
          accept={ACCEPTED_EXTENSIONS.join(',')}
          beforeUpload={handleUpload}
          showUploadList={false}
          disabled={isUploading}
          multiple={false}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: 36, color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">
            {t('common:aiProcessing.dragText', { defaultValue: '点击或拖拽文件到此区域上传' })}
          </p>
          <p className="ant-upload-hint">
            {t('common:aiProcessing.semantic.hint', {
              defaultValue: '支持 PDF、Word、Excel、CSV、PPT、HTML、TXT、音视频格式',
            })}
          </p>
        </Dragger>
      </Card>

      <ProcessingPanel origin="semantic" />

      <Card
        size="small"
        title={t('common:aiProcessing.semantic.jobListTitle', { defaultValue: '任务列表' })}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchJobs()}>
            {t('common:action.refresh', { defaultValue: '刷新' })}
          </Button>
        }
      >
        <Table<SemanticJob>
          rowKey="job_id"
          columns={jobColumns}
          dataSource={jobs}
          loading={isLoadingJobs}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={t('common:aiProcessing.semantic.recordsTitle', { defaultValue: '语义记录' })}
        open={recordModalOpen}
        onCancel={() => setRecordModalOpen(false)}
        footer={null}
        width={720}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Text>{t('common:aiProcessing.semantic.filterLabel', { defaultValue: '按类型筛选：' })}</Text>
              <Select
                allowClear
                placeholder={t('common:aiProcessing.semantic.allTypes', { defaultValue: '全部' })}
                value={recordTypeFilter}
                onChange={handleRecordTypeChange}
                style={{ width: 140 }}
                options={[
                  { value: 'entity', label: t('common:aiProcessing.semantic.entity', { defaultValue: '实体' }) },
                  { value: 'relationship', label: t('common:aiProcessing.semantic.relationship', { defaultValue: '关系' }) },
                  { value: 'summary', label: t('common:aiProcessing.semantic.summary', { defaultValue: '摘要' }) },
                ]}
              />
            </Space>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              disabled={selectedRecordKeys.length === 0}
              onClick={handleOpenTransferModal}
            >
              {t('aiProcessing:transfer.button')}
            </Button>
          </Space>
          <Table<SemanticRecord>
            rowKey="id"
            columns={recordColumns}
            dataSource={records}
            loading={isLoadingRecords}
            size="small"
            rowSelection={rowSelection}
            pagination={{
              current: recordPagination.page,
              pageSize: recordPagination.size,
              total: recordPagination.total,
              onChange: handleRecordPageChange,
            }}
          />
        </Space>
      </Modal>

      <TransferToLifecycleModal
        visible={transferModalVisible}
        onClose={() => setTransferModalVisible(false)}
        onSuccess={handleTransferSuccess}
        sourceType="semantic"
        selectedData={getSelectedRecordsData()}
      />
    </Space>
  );
};

export default SemanticContent;
