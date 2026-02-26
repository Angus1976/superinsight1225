/**
 * DesensitizerConfig — 脱敏规则配置、预览、完整性校验
 *
 * Embedded in Crowdsource task creation flow.
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Table, Select, Input, Switch, Button, Alert, Space, message, Modal,
} from 'antd';
import { PlusOutlined, DeleteOutlined, EyeOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  getDesensitizationRules,
  saveDesensitizationRules,
  previewDesensitization,
} from '@/services/aiAnnotationApi';
import type { DesensitizationRule, DesensitizationPreview } from '@/services/aiAnnotationApi';

interface DesensitizerConfigProps {
  taskId: string;
  sensitiveFields: string[];
  onValidationChange?: (isValid: boolean) => void;
}

const RULE_TYPES: DesensitizationRule['type'][] = ['name', 'phone', 'email', 'address', 'regex'];

const DEFAULT_REPLACEMENTS: Record<DesensitizationRule['type'], string> = {
  name: '***', phone: '****', email: '***@***.com', address: '[REDACTED]', regex: '***',
};

const DesensitizerConfig: React.FC<DesensitizerConfigProps> = ({
  taskId, sensitiveFields, onValidationChange,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [rules, setRules] = useState<DesensitizationRule[]>([]);
  const [previews, setPreviews] = useState<DesensitizationPreview[]>([]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Completeness validation: check all sensitiveFields covered by enabled rules
  const uncoveredFields = useMemo(() => {
    const coveredTypes = new Set(rules.filter((r) => r.enabled).map((r) => r.type));
    return sensitiveFields.filter((f) => !coveredTypes.has(f as DesensitizationRule['type']));
  }, [rules, sensitiveFields]);

  const isValid = uncoveredFields.length === 0 && rules.some((r) => r.enabled);

  useEffect(() => {
    onValidationChange?.(isValid);
  }, [isValid, onValidationChange]);

  // Load existing rules on mount
  useEffect(() => {
    getDesensitizationRules(taskId).then(setRules).catch(() => {
      message.error(t('ai_annotation:desensitizer.load_failed'));
    });
  }, [taskId, t]);

  const addRule = useCallback(() => {
    const type: DesensitizationRule['type'] = 'name';
    setRules((prev) => [...prev, {
      id: crypto.randomUUID?.() ?? Date.now().toString(),
      type,
      replacement: DEFAULT_REPLACEMENTS[type],
      enabled: true,
    }]);
  }, []);

  const deleteRule = useCallback((id: string) => {
    setRules((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const updateRule = useCallback((id: string, patch: Partial<DesensitizationRule>) => {
    setRules((prev) => prev.map((r) => {
      if (r.id !== id) return r;
      const updated = { ...r, ...patch };
      // Auto-fill replacement when type changes
      if (patch.type && !patch.replacement) {
        updated.replacement = DEFAULT_REPLACEMENTS[patch.type];
      }
      return updated;
    }));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await saveDesensitizationRules(taskId, rules);
      message.success(t('ai_annotation:desensitizer.save_success'));
    } catch {
      message.error(t('ai_annotation:desensitizer.save_failed'));
    } finally {
      setSaving(false);
    }
  }, [taskId, rules, t]);

  const handlePreview = useCallback(async () => {
    setLoading(true);
    try {
      const data = await previewDesensitization(taskId, rules);
      setPreviews(data.slice(0, 5));
      setPreviewOpen(true);
    } catch {
      message.error(t('ai_annotation:desensitizer.preview_failed'));
    } finally {
      setLoading(false);
    }
  }, [taskId, rules, t]);

  const columns: ColumnsType<DesensitizationRule> = [
    {
      title: t('ai_annotation:desensitizer.type'), dataIndex: 'type', key: 'type', width: 130,
      render: (_, r) => (
        <Select value={r.type} onChange={(v) => updateRule(r.id, { type: v })}
          style={{ width: 120 }} options={RULE_TYPES.map((v) => ({ label: t(`ai_annotation:desensitizer.type_${v}`), value: v }))} />
      ),
    },
    {
      title: t('ai_annotation:desensitizer.pattern'), dataIndex: 'pattern', key: 'pattern', width: 180,
      render: (_, r) => r.type === 'regex'
        ? <Input value={r.pattern} onChange={(e) => updateRule(r.id, { pattern: e.target.value })}
            placeholder={t('ai_annotation:desensitizer.pattern_placeholder')} />
        : <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: t('ai_annotation:desensitizer.replacement'), dataIndex: 'replacement', key: 'replacement', width: 160,
      render: (_, r) => (
        <Input value={r.replacement} onChange={(e) => updateRule(r.id, { replacement: e.target.value })} />
      ),
    },
    {
      title: t('ai_annotation:desensitizer.enabled'), dataIndex: 'enabled', key: 'enabled', width: 80,
      render: (_, r) => <Switch checked={r.enabled} onChange={(v) => updateRule(r.id, { enabled: v })} />,
    },
    {
      title: t('ai_annotation:desensitizer.actions'), key: 'actions', width: 80,
      render: (_, r) => (
        <Button size="small" danger icon={<DeleteOutlined />} onClick={() => deleteRule(r.id)} />
      ),
    },
  ];

  const previewColumns: ColumnsType<DesensitizationPreview> = [
    { title: t('ai_annotation:desensitizer.original'), dataIndex: 'original', key: 'original' },
    { title: t('ai_annotation:desensitizer.desensitized'), dataIndex: 'desensitized', key: 'desensitized' },
  ];

  return (
    <div className="desensitizer-config">
      {!isValid && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message={t('ai_annotation:desensitizer.incomplete_warning', {
            fields: uncoveredFields.join(', '),
          })} />
      )}

      <Card title={t('ai_annotation:desensitizer.title')} size="small"
        extra={
          <Space>
            <Button icon={<PlusOutlined />} onClick={addRule}>{t('ai_annotation:desensitizer.add_rule')}</Button>
            <Button icon={<EyeOutlined />} loading={loading} onClick={handlePreview}
              disabled={rules.length === 0}>{t('ai_annotation:desensitizer.preview')}</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
              {t('ai_annotation:desensitizer.save')}
            </Button>
          </Space>
        }>
        <Table<DesensitizationRule> dataSource={rules} columns={columns} rowKey="id"
          size="small" pagination={false} />
      </Card>

      <Modal title={t('ai_annotation:desensitizer.preview_title')} open={previewOpen}
        onCancel={() => setPreviewOpen(false)} footer={null} width={600}>
        <Table<DesensitizationPreview> dataSource={previews} columns={previewColumns}
          rowKey="original" size="small" pagination={false} />
      </Modal>
    </div>
  );
};

export default DesensitizerConfig;
