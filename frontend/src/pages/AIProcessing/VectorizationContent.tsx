/**
 * VectorizationContent — 向量化子 Tab
 *
 * Provides file upload, job list table, and vector record viewing
 * for the vectorization pipeline.
 */

import React, { useEffect, useCallback, useState, useRef } from 'react';
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
  Progress,
  Tooltip,
} from 'antd';
import {
  InboxOutlined,
  ReloadOutlined,
  EyeOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useVectorizationStore } from '@/stores/vectorizationStore';
import type { VectorizationJob, VectorRecord } from '@/stores/vectorizationStore';
import type { ColumnsType } from 'antd/es/table';
import TransferToLifecycleModal from '@/components/DataLifecycle/TransferToLifecycleModal';
import type { TransferDataItem } from '@/components/DataLifecycle/TransferToLifecycleModal';
import ProcessingPanel from './components/ProcessingPanel';

const { Dragger } = Upload;

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

const VectorizationContent: React.FC = () => {
  const { t } = useTranslation(['common', 'aiProcessing']);
  const {
    jobs, records, recordPagination,
    isUploading, isLoadingJobs, isLoadingRecords, error,
    uploadFile, fetchJobs, fetchRecords, clearError,
  } = useVectorizationStore();

  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedRecordKeys, setSelectedRecordKeys] = useState<React.Key[]>([]);
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [jobTransferModalOpen, setJobTransferModalOpen] = useState(false);
  const [transferJobId, setTransferJobId] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check if any jobs are actively processing
  const hasActiveJobs = jobs.some(
    (j) => j.status === 'pending' || j.status === 'extracting' || j.status === 'processing',
  );

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  // Auto-poll every 3s while there are active jobs
  useEffect(() => {
    if (hasActiveJobs) {
      pollingRef.current = setInterval(() => { fetchJobs(); }, 3000);
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [hasActiveJobs, fetchJobs]);

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

  const handleBatchTransfer = useCallback(() => {
    if (selectedRecordKeys.length === 0) {
      message.warning(t('aiProcessing:transfer.messages.noDataSelected'));
      return;
    }
    setTransferModalOpen(true);
  }, [selectedRecordKeys, t]);

  const handleTransferSuccess = useCallback(() => {
    setSelectedRecordKeys([]);
    setTransferModalOpen(false);
    message.success(t('aiProcessing:transfer.messages.success', { 
      count: selectedRecordKeys.length,
      stage: t('aiProcessing:transfer.stages.temp_data')
    }));
  }, [selectedRecordKeys, t]);

  const handleTransferClose = useCallback(() => {
    setTransferModalOpen(false);
  }, []);

  const handleJobTransfer = useCallback((jobId: string) => {
    setTransferJobId(jobId);
    setJobTransferModalOpen(true);
  }, []);

  const handleJobTransferSuccess = useCallback(() => {
    setJobTransferModalOpen(false);
    setTransferJobId(null);
    message.success(t('common:aiProcessing.vectorization.transferSuccess', { defaultValue: '数据已成功转存' }));
  }, [t]);

  const handleJobTransferClose = useCallback(() => {
    setJobTransferModalOpen(false);
    setTransferJobId(null);
  }, []);

  // Convert selected records to TransferDataItem format
  const getSelectedTransferData = useCallback((): TransferDataItem[] => {
    return records
      .filter(record => selectedRecordKeys.includes(record.id))
      .map(record => ({
        id: record.id,
        name: record.chunk_text.substring(0, 50) + (record.chunk_text.length > 50 ? '...' : ''),
        content: {
          text: record.chunk_text,
          chunk_index: record.chunk_index,
        },
        metadata: {
          ...record.metadata,
          created_at: record.created_at,
        },
      }));
  }, [records, selectedRecordKeys]);

  // Build transfer data for a completed job (all records)
  const getJobTransferData = useCallback((): TransferDataItem[] => {
    if (!transferJobId) return [];
    const job = jobs.find((j) => j.job_id === transferJobId);
    if (!job) return [];
    return [{
      id: job.job_id,
      name: job.file_name,
      content: {
        file_name: job.file_name,
        file_type: job.file_type,
        chunk_count: job.chunk_count,
      },
      metadata: {
        source: 'vectorization',
        created_at: job.created_at,
      },
    }];
  }, [transferJobId, jobs]);

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
        <Tag color={STATUS_COLOR[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: t('common:aiProcessing.columns.progress', { defaultValue: '进度' }),
      dataIndex: 'progress_info',
      width: 180,
      render: (_: unknown, record: VectorizationJob) => {
        const { status, progress_info } = record;
        if (status === 'completed') {
          return <Progress percent={100} size="small" status="success" />;
        }
        if (status === 'failed') {
          return <Progress percent={progress_info?.percent ?? 0} size="small" status="exception" />;
        }

        const percent = progress_info?.percent ?? 0;
        const stage = progress_info?.stage;
        const current = progress_info?.current ?? 0;
        const total = progress_info?.total ?? 0;

        if (total > 0) {
          const stageLabel = t(
            `common:aiProcessing.vectorization.progressStage.${stage || 'processing'}`,
            { defaultValue: stage || status },
          );
          return (
            <div>
              <Progress percent={percent} size="small" status="active" />
              <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{stageLabel} {current}/{total}</div>
            </div>
          );
        }

        return (
          <div style={{ fontSize: 12, color: '#999' }}>
            {t('common:aiProcessing.vectorization.progressStage.waiting', { defaultValue: '等待处理...' })}
          </div>
        );
      },
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
      width: 160,
      render: (_: unknown, record: VectorizationJob) => {
        const isCompleted = record.status === 'completed';
        return (
          <Space size="small">
            <Tooltip title={!isCompleted ? t('common:aiProcessing.vectorization.waitComplete', { defaultValue: '任务完成后可操作' }) : ''}>
              <span style={{ display: 'inline-block', cursor: !isCompleted ? 'not-allowed' : 'pointer' }}>
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!isCompleted}
                  style={!isCompleted ? { pointerEvents: 'none' } : undefined}
                  onClick={() => handleViewRecords(record.job_id)}
                >
                  {t('common:aiProcessing.viewRecords', { defaultValue: '查看' })}
                </Button>
              </span>
            </Tooltip>
            <Tooltip title={!isCompleted ? t('common:aiProcessing.vectorization.waitComplete', { defaultValue: '任务完成后可操作' }) : ''}>
              <span style={{ display: 'inline-block', cursor: !isCompleted ? 'not-allowed' : 'pointer' }}>
                <Button
                  type="link"
                  size="small"
                  icon={<CloudUploadOutlined />}
                  disabled={!isCompleted}
                  style={!isCompleted ? { pointerEvents: 'none' } : undefined}
                  onClick={() => handleJobTransfer(record.job_id)}
                >
                  {t('common:aiProcessing.vectorization.transfer', { defaultValue: '转存' })}
                </Button>
              </span>
            </Tooltip>
          </Space>
        );
      },
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

      <ProcessingPanel origin="vectorization" />

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
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {selectedRecordKeys.length > 0 && (
            <Alert
              message={t('aiProcessing:transfer.modal.selectedCount', { count: selectedRecordKeys.length })}
              type="info"
              showIcon
              action={
                <Button
                  size="small"
                  type="primary"
                  icon={<CloudUploadOutlined />}
                  onClick={handleBatchTransfer}
                >
                  {t('aiProcessing:transfer.button')}
                </Button>
              }
            />
          )}
          <Table<VectorRecord>
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
        visible={transferModalOpen}
        onClose={handleTransferClose}
        onSuccess={handleTransferSuccess}
        sourceType="vectorization"
        selectedData={getSelectedTransferData()}
      />

      <TransferToLifecycleModal
        visible={jobTransferModalOpen}
        onClose={handleJobTransferClose}
        onSuccess={handleJobTransferSuccess}
        sourceType="vectorization"
        selectedData={getJobTransferData()}
      />
    </Space>
  );
};

export default VectorizationContent;
