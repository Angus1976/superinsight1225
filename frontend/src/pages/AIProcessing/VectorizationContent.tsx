/**
 * VectorizationContent — 向量化子 Tab
 *
 * Provides file upload, job list table, and vector record viewing
 * for the vectorization pipeline.
 */

import React, { useEffect, useCallback, useState } from 'react';
import {
  Card,
  Upload,
  Table,
  Tag,
  Button,
  Space,
  message,
  Modal,
  Alert,
} from 'antd';
import {
  InboxOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useVectorizationStore } from '@/stores/vectorizationStore';
import type { VectorizationJob, VectorRecord } from '@/stores/vectorizationStore';
import type { ColumnsType } from 'antd/es/table';

const { Dragger } = Upload;

const ACCEPTED_EXTENSIONS = [
  '.pdf', '.csv', '.xlsx', '.xls', '.docx', '.html', '.htm', '.txt', '.md',
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

const VectorizationContent: React.FC = () => {
  const { t } = useTranslation(['common']);
  const {
    jobs, records, recordPagination,
    isUploading, isLoadingJobs, isLoadingRecords, error,
    uploadFile, fetchJobs, fetchRecords, clearError,
  } = useVectorizationStore();

  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

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
    fetchRecords(jobId);
  }, [fetchRecords]);

  const handleRecordPageChange = useCallback((page: number, pageSize: number) => {
    if (selectedJobId) fetchRecords(selectedJobId, page, pageSize);
  }, [selectedJobId, fetchRecords]);

  const jobColumns: ColumnsType<VectorizationJob> = [
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
      title: t('common:aiProcessing.columns.chunkCount', { defaultValue: '分块数' }),
      dataIndex: 'chunk_count',
      width: 80,
      render: (v: number | null) => v ?? '-',
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
      render: (_: unknown, record: VectorizationJob) => (
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

  const recordColumns: ColumnsType<VectorRecord> = [
    {
      title: t('common:aiProcessing.columns.chunkIndex', { defaultValue: '序号' }),
      dataIndex: 'chunk_index',
      width: 70,
    },
    {
      title: t('common:aiProcessing.columns.chunkText', { defaultValue: '文本内容' }),
      dataIndex: 'chunk_text',
      ellipsis: true,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {error && (
        <Alert type="error" message={error} closable onClose={clearError} />
      )}

      <Card size="small" title={t('common:aiProcessing.vectorization.uploadTitle', { defaultValue: '上传文件' })}>
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
            {t('common:aiProcessing.vectorization.hint', {
              defaultValue: '支持 PDF、Word、Excel、CSV、PPT、HTML、TXT、音视频格式',
            })}
          </p>
        </Dragger>
      </Card>

      <Card
        size="small"
        title={t('common:aiProcessing.vectorization.jobListTitle', { defaultValue: '任务列表' })}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchJobs()}>
            {t('common:action.refresh', { defaultValue: '刷新' })}
          </Button>
        }
      >
        <Table<VectorizationJob>
          rowKey="job_id"
          columns={jobColumns}
          dataSource={jobs}
          loading={isLoadingJobs}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={t('common:aiProcessing.vectorization.recordsTitle', { defaultValue: '向量记录' })}
        open={recordModalOpen}
        onCancel={() => setRecordModalOpen(false)}
        footer={null}
        width={720}
      >
        <Table<VectorRecord>
          rowKey="id"
          columns={recordColumns}
          dataSource={records}
          loading={isLoadingRecords}
          size="small"
          pagination={{
            current: recordPagination.page,
            pageSize: recordPagination.size,
            total: recordPagination.total,
            onChange: handleRecordPageChange,
          }}
        />
      </Modal>
    </Space>
  );
};

export default VectorizationContent;
