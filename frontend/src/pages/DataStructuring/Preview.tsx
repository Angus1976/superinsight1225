/**
 * Data Structuring — Content Preview Page
 *
 * Displays extracted content preview (text: first 500 chars, tabular: first 20 rows),
 * job processing status with steps indicator, and auto-polls while processing.
 * Navigates to Schema Editor when inference is complete.
 */

import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Card,
  Typography,
  Space,
  Spin,
  Alert,
  Button,
  Steps,
  Table,
  Result,
  Tag,
} from 'antd';
import {
  FileTextOutlined,
  TableOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  ArrowRightOutlined,
  ArrowLeftOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useStructuringStore } from '@/stores/structuringStore';
import type { JobStatus } from '@/stores/structuringStore';
import TransferToLifecycleModal from '@/components/DataLifecycle/TransferToLifecycleModal';
import type { TransferDataItem } from '@/components/DataLifecycle/TransferToLifecycleModal';

const { Title, Paragraph, Text } = Typography;

// ============================================================================
// Constants
// ============================================================================

const TEXT_PREVIEW_LIMIT = 500;
const TABLE_PREVIEW_ROWS = 20;
const POLL_INTERVAL_MS = 3000;

/** Statuses that indicate the job is still processing. */
const PROCESSING_STATUSES: JobStatus[] = [
  'pending',
  'extracting',
  'inferring',
  'extracting_entities',
];

/** Tabular file types that should render as a table preview. */
const TABULAR_FILE_TYPES = new Set(['csv', 'excel', 'xlsx', 'xls']);

// ============================================================================
// Status helpers
// ============================================================================

const STATUS_STEP_ORDER: JobStatus[] = [
  'pending',
  'extracting',
  'inferring',
  'confirming',
  'extracting_entities',
  'completed',
];

function getStepIndex(status: JobStatus): number {
  if (status === 'failed') return -1;
  return STATUS_STEP_ORDER.indexOf(status);
}

function isTabularFile(fileType: string): boolean {
  return TABULAR_FILE_TYPES.has(fileType.toLowerCase());
}

function isProcessing(status: JobStatus): boolean {
  return PROCESSING_STATUSES.includes(status);
}

// ============================================================================
// Sub-components
// ============================================================================

interface StatusStepsProps {
  status: JobStatus;
  t: (key: string, opts?: Record<string, unknown>) => string;
}

const StatusSteps: React.FC<StatusStepsProps> = ({ status, t }) => {
  const currentIndex = getStepIndex(status);
  const isFailed = status === 'failed';

  const steps = [
    { title: t('structuring:preview.stepPending', { defaultValue: '等待处理' }) },
    { title: t('structuring:preview.stepExtracting', { defaultValue: '内容提取' }) },
    { title: t('structuring:preview.stepInferring', { defaultValue: 'Schema 推断' }) },
    { title: t('structuring:preview.stepConfirming', { defaultValue: '等待确认' }) },
    { title: t('structuring:preview.stepExtractingEntities', { defaultValue: '实体提取' }) },
    { title: t('structuring:preview.stepCompleted', { defaultValue: '完成' }) },
  ];

  return (
    <Steps
      current={isFailed ? currentIndex : currentIndex}
      status={isFailed ? 'error' : undefined}
      items={steps}
      size="small"
    />
  );
};

interface TextPreviewProps {
  content: string;
  t: (key: string, opts?: Record<string, unknown>) => string;
}

const TextPreview: React.FC<TextPreviewProps> = ({ content, t }) => {
  const truncated = content.length > TEXT_PREVIEW_LIMIT;
  const displayText = truncated
    ? content.slice(0, TEXT_PREVIEW_LIMIT)
    : content;

  return (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          {t('structuring:preview.textPreviewTitle', { defaultValue: '文本内容预览' })}
          <Tag>{content.length} {t('structuring:preview.chars', { defaultValue: '字符' })}</Tag>
        </Space>
      }
    >
      <Paragraph
        style={{
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          maxHeight: 400,
          overflow: 'auto',
          background: '#fafafa',
          padding: 16,
          borderRadius: 6,
          fontFamily: 'monospace',
          fontSize: 13,
          lineHeight: 1.6,
        }}
      >
        {displayText}
        {truncated && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            ... ({t('structuring:preview.truncated', {
              total: content.length,
              limit: TEXT_PREVIEW_LIMIT,
              defaultValue: `已截断，共 ${content.length} 字符，仅显示前 ${TEXT_PREVIEW_LIMIT} 字符`,
            })})
          </Text>
        )}
      </Paragraph>
    </Card>
  );
};

interface TabularPreviewProps {
  content: string;
  t: (key: string, opts?: Record<string, unknown>) => string;
}

/**
 * Parse raw_content (stringified list of dicts) into rows for Ant Design Table.
 * The backend stores tabular preview as `str(preview_rows)` — a Python repr of
 * a list[dict]. We do a best-effort parse; if it fails we fall back to text.
 */
function parseTabularContent(raw: string): Record<string, string>[] | null {
  try {
    // The backend stores Python repr — try JSON first (works if keys use double quotes)
    const parsed = JSON.parse(raw.replace(/'/g, '"'));
    if (Array.isArray(parsed) && parsed.length > 0 && typeof parsed[0] === 'object') {
      return parsed as Record<string, string>[];
    }
  } catch {
    // Not valid JSON — fall through
  }
  return null;
}

const TabularPreview: React.FC<TabularPreviewProps> = ({ content, t }) => {
  const rows = useMemo(() => parseTabularContent(content), [content]);

  // Fallback to text preview if parsing fails
  if (!rows || rows.length === 0) {
    return <TextPreview content={content} t={t} />;
  }

  const displayRows = rows.slice(0, TABLE_PREVIEW_ROWS);
  const headers = Object.keys(rows[0]);

  const columns = headers.map((header) => ({
    title: header,
    dataIndex: header,
    key: header,
    ellipsis: true,
  }));

  const dataSource = displayRows.map((row, index) => ({
    ...row,
    _key: String(index),
  }));

  return (
    <Card
      title={
        <Space>
          <TableOutlined />
          {t('structuring:preview.tablePreviewTitle', { defaultValue: '表格内容预览' })}
          <Tag>{rows.length} {t('structuring:preview.rows', { defaultValue: '行' })}</Tag>
          <Tag>{headers.length} {t('structuring:preview.columns', { defaultValue: '列' })}</Tag>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={dataSource}
        rowKey="_key"
        pagination={false}
        scroll={{ x: 'max-content' }}
        size="small"
        bordered
      />
      {rows.length > TABLE_PREVIEW_ROWS && (
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          {t('structuring:preview.tableRowsTruncated', {
            shown: TABLE_PREVIEW_ROWS,
            total: rows.length,
            defaultValue: `仅显示前 ${TABLE_PREVIEW_ROWS} 行，共 ${rows.length} 行`,
          })}
        </Text>
      )}
    </Card>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const PreviewPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['structuring', 'common', 'aiProcessing']);
  const navigate = useNavigate();

  const { currentJob, isLoadingJob, error, fetchJob, clearError } =
    useStructuringStore();

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [transferModalOpen, setTransferModalOpen] = React.useState(false);

  // ---- Fetch job on mount and when jobId changes ----
  const loadJob = useCallback(() => {
    if (!jobId) return;
    fetchJob(jobId).catch(() => {
      // Error is captured in store
    });
  }, [jobId, fetchJob]);

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  // ---- Auto-poll while processing ----
  useEffect(() => {
    const shouldPoll =
      currentJob && isProcessing(currentJob.status) && jobId;

    if (shouldPoll) {
      pollTimerRef.current = setInterval(() => {
        fetchJob(jobId!).catch(() => {
          // Stop polling on error
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
        });
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [currentJob?.status, jobId, fetchJob]);

  // ---- Navigation handlers ----
  const handleGoToSchema = useCallback(() => {
    if (jobId) {
      navigate(`/data-structuring/schema/${jobId}`);
    }
  }, [jobId, navigate]);

  const handleGoBack = useCallback(() => {
    navigate('/data-structuring/upload');
  }, [navigate]);

  const handleGoToResults = useCallback(() => {
    if (jobId) {
      navigate(`/data-structuring/results/${jobId}`);
    }
  }, [jobId, navigate]);

  /** Build transfer data from the current job's raw content */
  const getTransferData = useCallback((): TransferDataItem[] => {
    if (!currentJob) return [];
    return [{
      id: currentJob.job_id,
      name: currentJob.file_name,
      content: { raw_content: currentJob.raw_content },
      metadata: {
        source_type: 'structuring',
        file_type: currentJob.file_type,
        status: currentJob.status,
      },
    }];
  }, [currentJob]);

  // ---- Guard: no jobId ----
  if (!jobId) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="404"
          title={t('structuring:preview.noJobId', { defaultValue: '未找到任务' })}
          extra={
            <Button type="primary" onClick={handleGoBack}>
              {t('structuring:preview.backToUpload', { defaultValue: '返回上传' })}
            </Button>
          }
        />
      </div>
    );
  }

  // ---- Loading state ----
  if (isLoadingJob && !currentJob) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 80 }}>
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />}
          tip={t('structuring:preview.loading', { defaultValue: '加载任务信息...' })}
        >
          <div style={{ height: 100 }} />
        </Spin>
      </div>
    );
  }

  // ---- Error state (no job loaded) ----
  if (error && !currentJob) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="error"
          title={t('structuring:preview.loadError', { defaultValue: '加载失败' })}
          subTitle={error}
          extra={[
            <Button key="retry" type="primary" onClick={loadJob}>
              {t('common:retry', { defaultValue: '重试' })}
            </Button>,
            <Button key="back" onClick={handleGoBack}>
              {t('structuring:preview.backToUpload', { defaultValue: '返回上传' })}
            </Button>,
          ]}
        />
      </div>
    );
  }

  if (!currentJob) return null;

  const { status, file_name, file_type, raw_content, error_message } =
    currentJob;
  const showContent = raw_content && raw_content.trim().length > 0;
  const canGoToSchema = status === 'confirming';
  const isCompleted = status === 'completed';
  const jobIsProcessing = isProcessing(status);

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <FileTextOutlined style={{ marginRight: 8 }} />
              {t('structuring:preview.title', { defaultValue: '内容预览' })}
            </Title>
            <Space>
              <Text type="secondary">{file_name}</Text>
              <Tag>{file_type.toUpperCase()}</Tag>
              {jobIsProcessing && (
                <Tag icon={<SyncOutlined spin />} color="processing">
                  {t('structuring:preview.processing', { defaultValue: '处理中' })}
                </Tag>
              )}
              {status === 'completed' && (
                <Tag icon={<CheckCircleOutlined />} color="success">
                  {t('structuring:preview.completed', { defaultValue: '已完成' })}
                </Tag>
              )}
              {status === 'failed' && (
                <Tag icon={<CloseCircleOutlined />} color="error">
                  {t('structuring:preview.failed', { defaultValue: '失败' })}
                </Tag>
              )}
              {status === 'confirming' && (
                <Tag icon={<ClockCircleOutlined />} color="warning">
                  {t('structuring:preview.awaitingConfirm', { defaultValue: '待确认 Schema' })}
                </Tag>
              )}
            </Space>
          </div>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleGoBack}>
              {t('structuring:preview.backToUpload', { defaultValue: '返回上传' })}
            </Button>
            {canGoToSchema && (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={handleGoToSchema}
              >
                {t('structuring:preview.goToSchema', { defaultValue: '继续编辑 Schema' })}
              </Button>
            )}
          </Space>
        </div>

        {/* Error alert */}
        {error && (
          <Alert
            message={t('structuring:preview.errorTitle', { defaultValue: '请求出错' })}
            description={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
          />
        )}

        {/* Job failure details */}
        {status === 'failed' && error_message && (
          <Alert
            message={t('structuring:preview.jobFailed', { defaultValue: '任务处理失败' })}
            description={error_message}
            type="error"
            showIcon
          />
        )}

        {/* Status steps */}
        <Card>
          <StatusSteps status={status} t={t} />
        </Card>

        {/* Content preview */}
        {showContent && (
          isTabularFile(file_type)
            ? <TabularPreview content={raw_content!} t={t} />
            : <TextPreview content={raw_content!} t={t} />
        )}

        {/* Processing spinner when no content yet */}
        {jobIsProcessing && !showContent && (
          <Card>
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin
                indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />}
                tip={t('structuring:preview.extracting', { defaultValue: '正在提取文件内容...' })}
              >
                <div style={{ height: 60 }} />
              </Spin>
            </div>
          </Card>
        )}

        {/* CTA when schema is ready */}
        {canGoToSchema && (
          <Card>
            <Result
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title={t('structuring:preview.schemaReady', { defaultValue: 'Schema 推断完成' })}
              subTitle={t('structuring:preview.schemaReadyHint', {
                defaultValue: '系统已自动推断数据 Schema，请前往编辑器确认或修改。',
              })}
              extra={
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowRightOutlined />}
                  onClick={handleGoToSchema}
                >
                  {t('structuring:preview.goToSchema', { defaultValue: '继续编辑 Schema' })}
                </Button>
              }
            />
          </Card>
        )}

        {/* CTA when job is completed */}
        {isCompleted && (
          <Card>
            <Result
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title={t('structuring:preview.completedTitle', { defaultValue: '数据结构化完成' })}
              subTitle={t('structuring:preview.completedHint', {
                defaultValue: '可查看结构化结果或直接转存到数据流转模块。',
              })}
              extra={
                <Space>
                  <Button
                    size="large"
                    icon={<DatabaseOutlined />}
                    onClick={() => setTransferModalOpen(true)}
                  >
                    {t('aiProcessing:transfer.button')}
                  </Button>
                  <Button
                    type="primary"
                    size="large"
                    icon={<ArrowRightOutlined />}
                    onClick={handleGoToResults}
                  >
                    {t('structuring:preview.viewResults', { defaultValue: '查看结构化结果' })}
                  </Button>
                </Space>
              }
            />
          </Card>
        )}
      </Space>

      {/* Transfer to Lifecycle Modal */}
      <TransferToLifecycleModal
        visible={transferModalOpen}
        onClose={() => setTransferModalOpen(false)}
        onSuccess={() => setTransferModalOpen(false)}
        sourceType="structuring"
        selectedData={getTransferData()}
      />
    </div>
  );
};

export default PreviewPage;
