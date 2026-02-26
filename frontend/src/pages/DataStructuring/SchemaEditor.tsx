/**
 * Data Structuring — Schema Editor Page
 *
 * Allows users to review and edit the AI-inferred schema before extraction.
 * Supports field add/delete/edit, type selection, confidence display,
 * and low-confidence warnings.
 */

import React, { useEffect, useCallback, useState, useMemo } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Table,
  Select,
  Input,
  Switch,
  Alert,
  Spin,
  Result,
  Tag,
  Popconfirm,
  message,
  Progress,
} from 'antd';
import {
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  WarningOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useStructuringStore } from '@/stores/structuringStore';
import type { SchemaField, FieldType, InferredSchema } from '@/stores/structuringStore';

const { Title, Text } = Typography;

// ============================================================================
// Constants
// ============================================================================

const LOW_CONFIDENCE_THRESHOLD = 0.3;
const MEDIUM_CONFIDENCE_THRESHOLD = 0.7;

const FIELD_TYPES: FieldType[] = [
  'string', 'integer', 'float', 'boolean', 'date', 'entity', 'list',
];

const ENTITY_TYPES = ['PERSON', 'ORG', 'LOCATION', 'DATE', 'MONEY', 'PRODUCT'];


function getConfidenceStatus(confidence: number): 'success' | 'normal' | 'exception' {
  if (confidence >= MEDIUM_CONFIDENCE_THRESHOLD) return 'success';
  if (confidence >= LOW_CONFIDENCE_THRESHOLD) return 'normal';
  return 'exception';
}

function createEmptyField(): SchemaField {
  return {
    name: '',
    field_type: 'string',
    description: '',
    required: false,
    entity_type: null,
  };
}

// ============================================================================
// Sub-components
// ============================================================================

interface ConfidenceBadgeProps {
  confidence: number;
  t: (key: string, opts?: Record<string, unknown>) => string;
}

const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence, t }) => {
  const percent = Math.round(confidence * 100);
  return (
    <Space direction="vertical" align="center" size={4}>
      <Progress
        type="circle"
        percent={percent}
        size={64}
        status={getConfidenceStatus(confidence)}
        format={() => `${percent}%`}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        {t('structuring:schema.overallConfidence', { defaultValue: '整体置信度' })}
      </Text>
    </Space>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const SchemaEditorPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['structuring', 'common']);
  const navigate = useNavigate();

  const {
    currentJob,
    schema,
    isLoadingJob,
    isConfirmingSchema,
    isExtracting,
    error,
    fetchJob,
    confirmSchema,
    startExtraction,
    clearError,
  } = useStructuringStore();

  const [fields, setFields] = useState<SchemaField[]>([]);
  const [hasEdited, setHasEdited] = useState(false);

  // Load job on mount
  useEffect(() => {
    if (!jobId) return;
    fetchJob(jobId).catch(() => {});
  }, [jobId, fetchJob]);

  // Sync fields from schema
  useEffect(() => {
    if (schema?.fields && !hasEdited) {
      setFields(schema.fields.map((f) => ({ ...f })));
    }
  }, [schema, hasEdited]);

  const confidence = useMemo(() => schema?.confidence ?? 0, [schema]);
  const isLowConfidence = confidence < LOW_CONFIDENCE_THRESHOLD;
  const isBusy = isConfirmingSchema || isExtracting;

  // ---- Field editing handlers ----
  const updateField = useCallback((index: number, patch: Partial<SchemaField>) => {
    setFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...patch };
      return next;
    });
    setHasEdited(true);
  }, []);

  const addField = useCallback(() => {
    setFields((prev) => [...prev, createEmptyField()]);
    setHasEdited(true);
  }, []);

  const removeField = useCallback((index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
    setHasEdited(true);
  }, []);

  // ---- Confirm & extract ----
  const handleConfirm = useCallback(async () => {
    if (!jobId || !schema) return;

    // Validate: all fields must have a name
    const emptyName = fields.some((f) => !f.name.trim());
    if (emptyName) {
      message.warning(
        t('structuring:schema.emptyFieldName', { defaultValue: '所有字段必须有名称' }),
      );
      return;
    }

    // Validate: field names must be unique
    const names = fields.map((f) => f.name.trim());
    if (new Set(names).size !== names.length) {
      message.warning(
        t('structuring:schema.duplicateFieldName', { defaultValue: '字段名称不能重复' }),
      );
      return;
    }

    const confirmedSchema: InferredSchema = {
      ...schema,
      fields,
    };

    try {
      await confirmSchema(jobId, confirmedSchema);
      await startExtraction(jobId);
      message.success(
        t('structuring:schema.confirmSuccess', { defaultValue: 'Schema 已确认，开始提取数据' }),
      );
      navigate(`/data-structuring/preview/${jobId}`);
    } catch {
      message.error(
        t('structuring:schema.confirmError', { defaultValue: '操作失败，请重试' }),
      );
    }
  }, [jobId, schema, fields, confirmSchema, startExtraction, navigate, t]);

  const handleGoBack = useCallback(() => {
    if (jobId) {
      navigate(`/data-structuring/preview/${jobId}`);
    }
  }, [jobId, navigate]);

  // ---- Table columns ----
  const columns = useMemo(() => [
    {
      title: t('structuring:schema.fieldName', { defaultValue: '字段名称' }),
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (_: string, __: SchemaField, index: number) => (
        <Input
          value={fields[index]?.name ?? ''}
          onChange={(e) => updateField(index, { name: e.target.value })}
          placeholder={t('structuring:schema.fieldNamePlaceholder', { defaultValue: '输入字段名' })}
          size="small"
        />
      ),
    },
    {
      title: t('structuring:schema.fieldType', { defaultValue: '类型' }),
      dataIndex: 'field_type',
      key: 'field_type',
      width: 130,
      render: (_: FieldType, __: SchemaField, index: number) => (
        <Select
          value={fields[index]?.field_type}
          onChange={(val: FieldType) => {
            const patch: Partial<SchemaField> = { field_type: val };
            if (val !== 'entity') patch.entity_type = null;
            updateField(index, patch);
          }}
          size="small"
          style={{ width: '100%' }}
          options={FIELD_TYPES.map((ft) => ({ label: ft, value: ft }))}
        />
      ),
    },
    {
      title: t('structuring:schema.description', { defaultValue: '描述' }),
      dataIndex: 'description',
      key: 'description',
      render: (_: string, __: SchemaField, index: number) => (
        <Input
          value={fields[index]?.description ?? ''}
          onChange={(e) => updateField(index, { description: e.target.value })}
          placeholder={t('structuring:schema.descriptionPlaceholder', { defaultValue: '字段描述' })}
          size="small"
        />
      ),
    },
    {
      title: t('structuring:schema.entityType', { defaultValue: '实体类型' }),
      dataIndex: 'entity_type',
      key: 'entity_type',
      width: 140,
      render: (_: string | null, __: SchemaField, index: number) => {
        if (fields[index]?.field_type !== 'entity') {
          return <Text type="secondary">—</Text>;
        }
        return (
          <Select
            value={fields[index]?.entity_type ?? undefined}
            onChange={(val: string) => updateField(index, { entity_type: val })}
            size="small"
            style={{ width: '100%' }}
            allowClear
            placeholder="PERSON, ORG..."
            options={ENTITY_TYPES.map((et) => ({ label: et, value: et }))}
          />
        );
      },
    },
    {
      title: t('structuring:schema.required', { defaultValue: '必填' }),
      dataIndex: 'required',
      key: 'required',
      width: 80,
      align: 'center' as const,
      render: (_: boolean, __: SchemaField, index: number) => (
        <Switch
          checked={fields[index]?.required ?? false}
          onChange={(checked) => updateField(index, { required: checked })}
          size="small"
        />
      ),
    },
    {
      title: t('structuring:schema.actions', { defaultValue: '操作' }),
      key: 'actions',
      width: 70,
      align: 'center' as const,
      render: (_: unknown, __: SchemaField, index: number) => (
        <Popconfirm
          title={t('structuring:schema.deleteConfirm', { defaultValue: '确定删除此字段？' })}
          onConfirm={() => removeField(index)}
          okText={t('common:confirm', { defaultValue: '确定' })}
          cancelText={t('common:cancel', { defaultValue: '取消' })}
        >
          <Button type="text" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ], [fields, updateField, removeField, t]);

  // ---- Guard: no jobId ----
  if (!jobId) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="404"
          title={t('structuring:schema.noJobId', { defaultValue: '未找到任务' })}
          extra={
            <Button type="primary" onClick={() => navigate('/data-structuring/upload')}>
              {t('structuring:schema.backToUpload', { defaultValue: '返回上传' })}
            </Button>
          }
        />
      </div>
    );
  }

  // ---- Loading ----
  if (isLoadingJob && !currentJob) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 80 }}>
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />}
          tip={t('structuring:schema.loading', { defaultValue: '加载 Schema...' })}
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
          title={t('structuring:schema.loadError', { defaultValue: '加载失败' })}
          subTitle={error}
          extra={
            <Button type="primary" onClick={() => fetchJob(jobId)}>
              {t('common:retry', { defaultValue: '重试' })}
            </Button>
          }
        />
      </div>
    );
  }

  // ---- No schema available ----
  if (!schema || fields.length === 0) {
    if (isLoadingJob) {
      return (
        <div style={{ padding: 24, textAlign: 'center', marginTop: 80 }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />}>
            <div style={{ height: 100 }} />
          </Spin>
        </div>
      );
    }
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="info"
          title={t('structuring:schema.noSchema', { defaultValue: 'Schema 尚未就绪' })}
          subTitle={t('structuring:schema.noSchemaHint', {
            defaultValue: '请等待 AI 推断完成，或返回预览页查看进度。',
          })}
          extra={
            <Button type="primary" onClick={handleGoBack}>
              {t('structuring:schema.backToPreview', { defaultValue: '返回预览' })}
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <EditOutlined style={{ marginRight: 8 }} />
              {t('structuring:schema.title', { defaultValue: 'Schema 编辑器' })}
            </Title>
            {currentJob && (
              <Space>
                <Text type="secondary">{currentJob.file_name}</Text>
                <Tag>{currentJob.file_type.toUpperCase()}</Tag>
              </Space>
            )}
          </div>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleGoBack}>
              {t('structuring:schema.backToPreview', { defaultValue: '返回预览' })}
            </Button>
            <ConfidenceBadge confidence={confidence} t={t} />
          </Space>
        </div>

        {/* Error alert */}
        {error && (
          <Alert
            message={t('structuring:schema.errorTitle', { defaultValue: '请求出错' })}
            description={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
          />
        )}

        {/* Low confidence warning */}
        {isLowConfidence && (
          <Alert
            message={t('structuring:schema.lowConfidenceTitle', { defaultValue: '低置信度警告' })}
            description={t('structuring:schema.lowConfidenceDesc', {
              defaultValue: 'AI 推断的 Schema 置信度较低（< 30%），建议仔细检查并手动编辑字段。',
            })}
            type="warning"
            showIcon
            icon={<WarningOutlined />}
          />
        )}

        {/* Source description */}
        {schema.source_description && (
          <Card size="small">
            <Text type="secondary">
              {t('structuring:schema.sourceDesc', { defaultValue: '数据源描述' })}：
            </Text>{' '}
            <Text>{schema.source_description}</Text>
          </Card>
        )}

        {/* Schema fields table */}
        <Card
          title={
            <Space>
              {t('structuring:schema.fieldsTitle', { defaultValue: 'Schema 字段' })}
              <Tag>{fields.length} {t('structuring:schema.fieldsCount', { defaultValue: '个字段' })}</Tag>
            </Space>
          }
          extra={
            <Button type="dashed" icon={<PlusOutlined />} onClick={addField} size="small">
              {t('structuring:schema.addField', { defaultValue: '添加字段' })}
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={fields}
            rowKey={(_, index) => String(index)}
            pagination={false}
            size="small"
            bordered
            scroll={{ x: 'max-content' }}
          />
        </Card>

        {/* Confirm button */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <Button onClick={handleGoBack}>
              {t('common:cancel', { defaultValue: '取消' })}
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={handleConfirm}
              loading={isBusy}
              disabled={fields.length === 0}
              size="large"
            >
              {t('structuring:schema.confirmAndExtract', { defaultValue: '确认 Schema 并开始提取' })}
            </Button>
          </div>
        </Card>
      </Space>
    </div>
  );
};

export default SchemaEditorPage;
