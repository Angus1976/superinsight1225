/**
 * TranslationEditor Component (翻译编辑器)
 * 
 * Form for adding/editing translations with:
 * - Fields for each supported language
 * - Highlight missing translations
 * - Bulk import/export translations
 * 
 * Requirements: 3.1, 3.4
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Form,
  Input,
  Button,
  Space,
  Modal,
  Tag,
  message,
  Empty,
  Progress,
  Upload,
  Tooltip,
  Row,
  Col,
  Typography,
  Alert,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DownloadOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  GlobalOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';
import {
  ontologyI18nApi,
  type OntologyTranslation,
} from '../../services/ontologyExpertApi';

const { TextArea } = Input;
const { Text, Title } = Typography;

interface TranslationRecord {
  element_id: string;
  element_type: string;
  translations: Record<string, OntologyTranslation>;
}

interface TranslationEditorProps {
  ontologyId: string;
  onTranslationChange?: () => void;
}

const SUPPORTED_LANGUAGES = [
  { code: 'zh-CN', name: '简体中文', required: true },
  { code: 'en-US', name: 'English', required: true },
  { code: 'zh-TW', name: '繁體中文', required: false },
  { code: 'ja-JP', name: '日本語', required: false },
  { code: 'ko-KR', name: '한국어', required: false },
];

const TranslationEditor: React.FC<TranslationEditorProps> = ({
  ontologyId,
  onTranslationChange,
}) => {
  const { t } = useTranslation('ontology');
  const [records, setRecords] = useState<TranslationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<TranslationRecord | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'complete' | 'incomplete'>('all');
  const [missingCounts, setMissingCounts] = useState<Record<string, number>>({});

  // Load missing translation counts
  const loadMissingCounts = useCallback(async () => {
    const counts: Record<string, number> = {};
    for (const lang of SUPPORTED_LANGUAGES) {
      try {
        const missing = await ontologyI18nApi.getMissingTranslations(ontologyId, lang.code);
        counts[lang.code] = missing.length;
      } catch (error) {
        counts[lang.code] = 0;
      }
    }
    setMissingCounts(counts);
  }, [ontologyId]);

  useEffect(() => {
    loadMissingCounts();
  }, [loadMissingCounts]);

  const handleEdit = (record: TranslationRecord) => {
    setEditingRecord(record);
    
    // Prepare form values
    const formValues: Record<string, string> = {
      element_id: record.element_id,
    };
    
    SUPPORTED_LANGUAGES.forEach((lang) => {
      const translation = record.translations[lang.code];
      if (translation) {
        formValues[`${lang.code}_name`] = translation.name;
        formValues[`${lang.code}_description`] = translation.description || '';
        formValues[`${lang.code}_help_text`] = translation.help_text || '';
      }
    });
    
    form.setFieldsValue(formValues);
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const elementId = editingRecord?.element_id || values.element_id;

      // Save translations for each language
      for (const lang of SUPPORTED_LANGUAGES) {
        const name = values[`${lang.code}_name`];
        if (name) {
          await ontologyI18nApi.addTranslation(elementId, {
            language: lang.code,
            name,
            description: values[`${lang.code}_description`],
            help_text: values[`${lang.code}_help_text`],
          });
        }
      }

      message.success(t('i18n.saveSuccess'));
      setModalVisible(false);
      form.resetFields();
      loadMissingCounts();
      onTranslationChange?.();
    } catch (error) {
      console.error('Failed to save translation:', error);
      message.error(t('i18n.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (language: string) => {
    try {
      const data = await ontologyI18nApi.exportTranslations(ontologyId, language);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `translations_${language}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(t('i18n.exportSuccess'));
    } catch (error) {
      console.error('Failed to export translations:', error);
      message.error(t('i18n.exportFailed'));
    }
  };

  const handleImport = async (file: File, language: string) => {
    try {
      const text = await file.text();
      const translations = JSON.parse(text);
      await ontologyI18nApi.importTranslations(ontologyId, language, translations);
      message.success(t('i18n.importSuccess'));
      loadMissingCounts();
      onTranslationChange?.();
    } catch (error) {
      console.error('Failed to import translations:', error);
      message.error(t('i18n.importFailed'));
    }
    return false; // Prevent default upload behavior
  };

  const getTranslationStatus = (record: TranslationRecord) => {
    const requiredLangs = SUPPORTED_LANGUAGES.filter((l) => l.required);
    const hasAllRequired = requiredLangs.every(
      (lang) => record.translations[lang.code]?.name
    );
    return hasAllRequired ? 'complete' : 'incomplete';
  };

  const calculateCoverage = () => {
    const totalRequired = SUPPORTED_LANGUAGES.filter((l) => l.required).length;
    const totalMissing = Object.entries(missingCounts)
      .filter(([code]) => SUPPORTED_LANGUAGES.find((l) => l.code === code)?.required)
      .reduce((sum, [, count]) => sum + count, 0);
    
    if (totalMissing === 0) return 100;
    // This is a simplified calculation
    return Math.max(0, 100 - (totalMissing * 10));
  };

  const renderLanguageTab = (language: typeof SUPPORTED_LANGUAGES[0]) => (
    <Card size="small">
      <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Space>
            <GlobalOutlined />
            <Text strong>{language.name}</Text>
            {language.required && <Tag color="red">{t('template.required')}</Tag>}
            {missingCounts[language.code] > 0 && (
              <Tag color="warning" icon={<WarningOutlined />}>
                {t('i18n.missingCount', { count: missingCounts[language.code] })}
              </Tag>
            )}
          </Space>
        </Col>
        <Col>
          <Space>
            <Upload
              accept=".json"
              showUploadList={false}
              beforeUpload={(file) => handleImport(file, language.code)}
            >
              <Button icon={<UploadOutlined />} size="small">
                {t('i18n.importTranslations')}
              </Button>
            </Upload>
            <Button
              icon={<DownloadOutlined />}
              size="small"
              onClick={() => handleExport(language.code)}
            >
              {t('i18n.exportTranslations')}
            </Button>
          </Space>
        </Col>
      </Row>

      {missingCounts[language.code] === 0 ? (
        <Alert
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          message={t('i18n.noMissingTranslations')}
        />
      ) : (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message={t('i18n.missingCount', { count: missingCounts[language.code] })}
          description={t('i18n.warningMissingTranslation')}
        />
      )}
    </Card>
  );

  return (
    <div>
      {/* Header with Coverage */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col span={8}>
            <Title level={4} style={{ margin: 0 }}>
              <GlobalOutlined /> {t('i18n.translationEditor')}
            </Title>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <Text type="secondary">{t('i18n.translationCoverage')}</Text>
              <Progress
                percent={calculateCoverage()}
                status={calculateCoverage() === 100 ? 'success' : 'active'}
                strokeColor={calculateCoverage() === 100 ? '#52c41a' : '#1890ff'}
              />
            </div>
          </Col>
          <Col span={8} style={{ textAlign: 'right' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingRecord(null);
                form.resetFields();
                setModalVisible(true);
              }}
            >
              {t('i18n.addTranslation')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Language Tabs */}
      <Card>
        <Tabs
          items={SUPPORTED_LANGUAGES.map((lang) => ({
            key: lang.code,
            label: (
              <Space>
                {lang.name}
                {missingCounts[lang.code] > 0 && (
                  <Tag color="warning">{missingCounts[lang.code]}</Tag>
                )}
              </Space>
            ),
            children: renderLanguageTab(lang),
          }))}
        />
      </Card>

      {/* Edit Modal */}
      <Modal
        title={t(editingRecord ? 'i18n.editTranslation' : 'i18n.addTranslation')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={saving}
        width={800}
      >
        <Form form={form} layout="vertical">
          {!editingRecord && (
            <Form.Item
              name="element_id"
              label={t('i18n.elementId')}
              rules={[{ required: true }]}
            >
              <Input placeholder="entity_type_001" />
            </Form.Item>
          )}

          <Tabs
            items={SUPPORTED_LANGUAGES.map((lang) => ({
              key: lang.code,
              label: (
                <Space>
                  {lang.name}
                  {lang.required && <Tag color="red" size="small">*</Tag>}
                </Space>
              ),
              children: (
                <div>
                  <Form.Item
                    name={`${lang.code}_name`}
                    label={t('i18n.translationName')}
                    rules={lang.required ? [{ required: true }] : []}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name={`${lang.code}_description`}
                    label={t('i18n.translationDescription')}
                  >
                    <TextArea rows={2} />
                  </Form.Item>
                  <Form.Item
                    name={`${lang.code}_help_text`}
                    label={t('i18n.translationHelpText')}
                  >
                    <TextArea rows={2} />
                  </Form.Item>
                </div>
              ),
            }))}
          />
        </Form>
      </Modal>
    </div>
  );
};

export default TranslationEditor;
