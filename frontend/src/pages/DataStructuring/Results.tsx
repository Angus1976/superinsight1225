/**
 * Data Structuring — Results Page
 *
 * Displays structured records in a dynamic table based on the job's schema,
 * with pagination, confidence indicators, source span tooltips,
 * and a "Create Annotation Task" button for completed jobs.
 */

import React, { useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Table,
  Tag,
  Tooltip,
  Spin,
  Result,
  Alert,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  PlusOutlined,
  TableOutlined,
  InfoCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useStructuringStore } from '@/stores/structuringStore';
import type { SchemaField, StructuredRecord } from '@/stores/structuringStore';
import { useTempData } from '@/hooks/useDataLifecycle';

const { Title, Text } = Typography;

// ============================================================================
// Constants
// ============================================================================

const SOURCE_SPAN_TRUNCATE = 80;

// ============================================================================
// Helpers
// ============================================================================

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'green';
  if (confidence >= 0.5) return 'orange';
  return 'red';
}

function truncateText(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

// ============================================================================
// Main Component
// ============================================================================

const ResultsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['structuring', 'common']);
  const navigate = useNavigate();

  const {
    currentJob,
    records,
    recordPagination,
    isLoadingJob,
    isLoadingRecords,
    isCreatingTasks,
    error,
    fetchJob,
    fetchRecords,
    createAnnotationTasks,
    clearError,
  } = useStructuringStore();

  const { createTempData, loading: isTransferring } = useTempData();

  // ---- Load job + records on mount ----
  useEffect(() => {
    if (!jobId) return;
    fetchJob(jobId).catch(() => {});
    fetchRecords(jobId).catch(() => {});
  }, [jobId, fetchJob, fetchRecords]);

  // ---- Schema fields for dynamic columns ----
  const schemaFields: SchemaField[] = useMemo(() => {
    if (!currentJob) return [];
    const schema = currentJob.confirmed_schema ?? currentJob.inferred_schema;
    return schema?.fields ?? [];
  }, [currentJob]);

  // ---- Pagination handler ----
  const handlePageChange = useCallback(
    (page: number, pageSize: number) => {
      if (!jobId) return;
      fetchRecords(jobId, page, pageSize).catch(() => {});
    },
    [jobId, fetchRecords],
  );

  // ---- Create annotation tasks ----
  const handleCreateTasks = useCallback(async () => {
    if (!jobId) return;
    try {
      await createAnnotationTasks(jobId);
      message.success(
        t('structuring:results.createTasksSuccess', {
          defaultValue: '标注任务创建成功',
        }),
      );
    } catch {
      message.error(
        t('structuring:results.createTasksError', {
          defaultValue: '创建标注任务失败，请重试',
        }),
      );
    }
  }, [jobId, createAnnotationTasks, t]);

  // ---- Transfer to lifecycle ----
  const handleTransferToLifecycle = useCallback(async () => {
    if (!currentJob || records.length === 0) return;
    
    try {
      // Create temp data entries for each record
      const promises = records.map((record) =>
        createTempData({
          name: `${currentJob.file_name}_record_${record.id}`,
          content: record.fields,
          metadata: {
            source_type: 'structuring',
            source_id: currentJob.job_id,
            file_name: currentJob.file_name,
            file_type: currentJob.file_type,
            confidence: record.confidence,
            source_span: record.source_span,
          },
        })
      );

      await Promise.all(promises);
      
      message.success(
        t('structuring:results.transferSuccess', {
          count: records.length,
          defaultValue: `已成功转移 ${records.length} 条记录到数据生命周期`,
        }),
      );
      
      // Navigate to data lifecycle page
      navigate('/data-lifecycle');
    } catch {
      message.error(
        t('structuring:results.transferError', {
          defaultValue: '转移到数据生命周期失败，请重试',
        }),
      );
    }
  }, [currentJob, records, createTempData, navigate, t]);

  // ---- Navigation ----
  const handleGoBack = useCallback(() => {
    if (jobId) {
      navigate(`/data-structuring/preview/${jobId}`);
    }
  }, [jobId, navigate]);

  // ---- Build dynamic table columns ----
  const columns = useMemo(() => {
    const schemaCols = schemaFields.map((field) => ({
      title: field.name,
      dataIndex: ['fields', field.name],
      key: field.name,
      ellipsis: true,
      render: (value: unknown) => {
        if (value === null || value === undefined) {
          return <Text type="secondary">—</Text>;
        }
        if (typeof value === 'boolean') {
          return value ? <Tag color="blue">true</Tag> : <Tag>false</Tag>;
        }
        if (Array.isArray(value)) {
          return value.map((v, i) => (
            <Tag key={i}>{String(v)}</Tag>
          ));
        }
        return String(value);
      },
    }));

    // Confidence column
    schemaCols.push({
      title: t('structuring:results.confidence', { defaultValue: '置信度' }),
      dataIndex: 'confidence' as any,
      key: '_confidence',
      ellipsis: false,
      render: (_: unknown, record: StructuredRecord) => {
        const pct = Math.round(record.confidence * 100);
        return (
          <Tag color={getConfidenceColor(record.confidence)}>
            {pct}%
          </Tag>
        );
      },
    } as any);

    // Source span column
    schemaCols.push({
      title: t('structuring:results.sourceSpan', { defaultValue: '原文引用' }),
      dataIndex: 'source_span' as any,
      key: '_source_span',
      ellipsis: false,
      render: (_: unknown, record: StructuredRecord) => {
        if (!record.source_span) {
          return <Text type="secondary">—</Text>;
        }
        if (record.source_span.length <= SOURCE_SPAN_TRUNCATE) {
          return <Text style={{ fontSize: 12 }}>{record.source_span}</Text>;
        }
        return (
          <Tooltip title={record.source_span} overlayStyle={{ maxWidth: 400 }}>
            <Text style={{ fontSize: 12, cursor: 'pointer' }}>
              {truncateText(record.source_span, SOURCE_SPAN_TRUNCATE)}{' '}
              <InfoCircleOutlined />
            </Text>
          </Tooltip>
        );
      },
    } as any);

    return schemaCols;
  }, [schemaFields, t]);

  // ---- Guard: no jobId ----
  if (!jobId) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="404"
          title={t('structuring:results.noJobId', { defaultValue: '未找到任务' })}
          extra={
            <Button type="primary" onClick={() => navigate('/data-structuring/upload')}>
              {t('structuring:results.backToUpload', { defaultValue: '返回上传' })}
            </Button>
          }
        />
      </div>
    );
  }

  // ---- Loading (no job yet) ----
  if (isLoadingJob && !currentJob) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 80 }}>
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />}
          tip={t('structuring:results.loading', { defaultValue: '加载结果...' })}
        >
          <div style={{ height: 100 }} />
        </Spin>
      </div>
    );
  }

  // ---- Error (no job) ----
  if (error && !currentJob) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="error"
          title={t('structuring:results.loadError', { defaultValue: '加载失败' })}
          subTitle={error}
          extra={[
            <Button key="retry" type="primary" onClick={() => fetchJob(jobId)}>
              {t('common:retry', { defaultValue: '重试' })}
            </Button>,
            <Button key="back" onClick={handleGoBack}>
              {t('structuring:results.backToPreview', { defaultValue: '返回预览' })}
            </Button>,
          ]}
        />
      </div>
    );
  }

  if (!currentJob) return null;

  const isCompleted = currentJob.status === 'completed';

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <TableOutlined style={{ marginRight: 8 }} />
              {t('structuring:results.title', { defaultValue: '结构化结果' })}
            </Title>
            <Space>
              <Text type="secondary">{currentJob.file_name}</Text>
              <Tag>{currentJob.file_type.toUpperCase()}</Tag>
              <Tag color="blue">
                {recordPagination.total}{' '}
                {t('structuring:results.recordCount', { defaultValue: '条记录' })}
              </Tag>
            </Space>
          </div>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleGoBack}>
              {t('structuring:results.backToPreview', { defaultValue: '返回预览' })}
            </Button>
            {isCompleted && records.length > 0 && (
              <>
                <Button
                  icon={<DatabaseOutlined />}
                  onClick={handleTransferToLifecycle}
                  loading={isTransferring}
                >
                  {t('structuring:results.transferToLifecycle', { defaultValue: '转移到生命周期' })}
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreateTasks}
                  loading={isCreatingTasks}
                >
                  {t('structuring:results.createTasks', { defaultValue: '创建标注任务' })}
                </Button>
              </>
            )}
          </Space>
        </div>

        {/* Error alert */}
        {error && (
          <Alert
            message={t('structuring:results.errorTitle', { defaultValue: '请求出错' })}
            description={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
          />
        )}

        {/* Schema info */}
        {schemaFields.length > 0 && (
          <Card size="small">
            <Space wrap>
              <Text type="secondary">
                {t('structuring:results.schemaInfo', { defaultValue: 'Schema 字段' })}:
              </Text>
              {schemaFields.map((field) => (
                <Tag key={field.name}>
                  {field.name}{' '}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    ({field.field_type})
                  </Text>
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        {/* Records table */}
        <Card>
          <Table
            columns={columns}
            dataSource={records}
            rowKey="id"
            loading={isLoadingRecords}
            pagination={{
              current: recordPagination.page,
              pageSize: recordPagination.size,
              total: recordPagination.total,
              onChange: handlePageChange,
              showSizeChanger: true,
              showTotal: (total) =>
                t('structuring:results.paginationTotal', {
                  total,
                  defaultValue: `共 ${total} 条`,
                }),
            }}
            scroll={{ x: 'max-content' }}
            size="middle"
            bordered
          />
        </Card>

        {/* Completed CTA */}
        {isCompleted && records.length > 0 && (
          <Card>
            <Result
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title={t('structuring:results.completedTitle', {
                defaultValue: '数据结构化完成',
              })}
              subTitle={t('structuring:results.completedHint', {
                count: recordPagination.total,
                defaultValue: `共提取 ${recordPagination.total} 条结构化记录，可创建标注任务。`,
              })}
              extra={
                <Button
                  type="primary"
                  size="large"
                  icon={<PlusOutlined />}
                  onClick={handleCreateTasks}
                  loading={isCreatingTasks}
                >
                  {t('structuring:results.createTasks', { defaultValue: '创建标注任务' })}
                </Button>
              }
            />
          </Card>
        )}
      </Space>
    </div>
  );
};

export default ResultsPage;
