/**
 * ExternalAnnotationView — Independent external annotation page
 *
 * Route: /external-annotation/:token
 * No main system login required.
 * Validates: Requirements 4.5, 4.6
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Alert, Spin, Result, Input, Space, message } from 'antd';
import { SendOutlined, HomeOutlined } from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  getExternalTask,
  submitExternalAnnotation,
  validateAnnotations,
} from '@/services/aiAnnotationApi';
import type { AnnotationTask } from '@/services/aiAnnotationApi';

type Status = 'loading' | 'ready' | 'error' | 'submitted';

const ExternalAnnotationView: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const { t } = useTranslation(['ai_annotation']);

  const [status, setStatus] = useState<Status>('loading');
  const [task, setTask] = useState<AnnotationTask | null>(null);
  const [data, setData] = useState<unknown[]>([]);
  const [annotations, setAnnotations] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }
    loadTask(token);
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadTask = useCallback(async (tk: string) => {
    setStatus('loading');
    try {
      const result = await getExternalTask(tk);
      setTask(result.task);
      setData(result.data);
      setStatus('ready');
    } catch {
      setStatus('error');
    }
  }, []);

  const handleAnnotationChange = useCallback((index: number, value: string) => {
    setAnnotations((prev) => ({ ...prev, [index]: value }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!token || !task) return;

    setSubmitting(true);
    setValidationError(null);

    try {
      // Quality validation before submit
      const validation = await validateAnnotations({
        project_id: task.project_id,
        validation_types: ['completeness', 'consistency'],
      });

      if (validation.status !== 'valid' && validation.status !== 'success') {
        setValidationError(t('ai_annotation:external.validation_failed'));
        setSubmitting(false);
        return;
      }

      const payload = data.map((item, i) => ({
        data: item,
        annotation: annotations[i] ?? '',
      }));

      await submitExternalAnnotation(token, payload);
      message.success(t('ai_annotation:external.submit_success'));
      setStatus('submitted');
    } catch {
      message.error(t('ai_annotation:external.submit_failed'));
    } finally {
      setSubmitting(false);
    }
  }, [token, task, data, annotations, t]);

  if (status === 'loading') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <Spin size="large" tip={t('ai_annotation:external.loading')} />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <Result
        status="warning"
        title={t('ai_annotation:external.invalid_token')}
        subTitle={t('ai_annotation:external.invalid_token_desc')}
        extra={
          <Button icon={<HomeOutlined />} href="/">
            {t('ai_annotation:external.back_to_home')}
          </Button>
        }
      />
    );
  }

  if (status === 'submitted') {
    return (
      <Result
        status="success"
        title={t('ai_annotation:external.submit_success')}
        extra={
          <Button icon={<HomeOutlined />} href="/">
            {t('ai_annotation:external.back_to_home')}
          </Button>
        }
      />
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '24px auto', padding: '0 16px' }}>
      <Card title={t('ai_annotation:external.title')} style={{ marginBottom: 16 }}>
        {task && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div><strong>{t('ai_annotation:external.task_title')}:</strong> {task.title}</div>
            <div><strong>{t('ai_annotation:external.project')}:</strong> {task.project_name}</div>
            <div><strong>{t('ai_annotation:external.data_count')}:</strong> {data.length}</div>
          </Space>
        )}
      </Card>

      {validationError && (
        <Alert type="warning" showIcon closable message={validationError} style={{ marginBottom: 16 }} />
      )}

      {data.length === 0 ? (
        <Alert type="info" message={t('ai_annotation:external.no_data')} />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {data.map((item, index) => (
            <Card key={index} size="small" title={t('ai_annotation:external.item_index', { index: index + 1 })}>
              <pre style={{ whiteSpace: 'pre-wrap', marginBottom: 12, background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {typeof item === 'string' ? item : JSON.stringify(item, null, 2)}
              </pre>
              <Input.TextArea
                rows={2}
                value={annotations[index] ?? ''}
                onChange={(e) => handleAnnotationChange(index, e.target.value)}
                placeholder={t('ai_annotation:external.annotation_area')}
              />
            </Card>
          ))}

          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={submitting}
            onClick={handleSubmit}
            block
            size="large"
          >
            {submitting ? t('ai_annotation:external.submitting') : t('ai_annotation:external.submit')}
          </Button>
        </Space>
      )}
    </div>
  );
};

export default ExternalAnnotationView;
