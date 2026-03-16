/**
 * Template Export/Import Component (模板导出导入)
 * 
 * Handles exporting templates to JSON/YAML and importing templates from files.
 * Validates imported templates and shows import preview.
 * 
 * Requirements: Task 21.4 - Template Management
 * Validates: Requirements 12.4
 */

import React, { useState, useCallback } from 'react';
import {
  Modal,
  Card,
  Upload,
  Button,
  Radio,
  Typography,
  Space,
  Alert,
  Descriptions,
  Tag,
  Divider,
  Row,
  Col,
  Spin,
  message,
  Result,
  Table,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import {
  UploadOutlined,
  DownloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  NodeIndexOutlined,
  BranchesOutlined,
  SafetyCertificateOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  ontologyTemplateApi,
  OntologyTemplate,
} from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;

type ExportFormat = 'json' | 'yaml';

interface TemplateExportImportProps {
  template?: OntologyTemplate | null;
  mode: 'export' | 'import';
  visible: boolean;
  onClose: () => void;
  onImportSuccess?: (template: OntologyTemplate) => void;
}

interface ImportPreview {
  template: OntologyTemplate;
  validationErrors: string[];
  validationWarnings: string[];
}

const TemplateExportImport: React.FC<TemplateExportImportProps> = ({
  template,
  mode,
  visible,
  onClose,
  onImportSuccess,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async ({ templateId, format }: { templateId: string; format: ExportFormat }) => {
      const blob = await ontologyTemplateApi.exportTemplate(templateId, format);
      return { blob, format };
    },
    onSuccess: ({ blob, format }) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${template?.name || 'template'}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      message.success(t('ontology:template.exportSuccess'));
      handleClose();
    },
    onError: () => {
      message.error(t('ontology:template.exportFailed'));
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async (templateData: Record<string, unknown>) => {
      return ontologyTemplateApi.importTemplate(templateData, 'json');
    },
    onSuccess: (result) => {
      message.success(t('ontology:template.importSuccess'));
      onImportSuccess?.(result);
      handleClose();
    },
    onError: () => {
      message.error(t('ontology:template.importFailed'));
    },
  });

  // Reset state when modal closes
  const handleClose = () => {
    setFileList([]);
    setImportPreview(null);
    setParseError(null);
    setExportFormat('json');
    onClose();
  };

  // Handle export
  const handleExport = () => {
    if (!template) return;
    exportMutation.mutate({ templateId: template.id, format: exportFormat });
  };

  // Validate imported template
  const validateTemplate = (data: Record<string, unknown>): { errors: string[]; warnings: string[] } => {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Required fields
    if (!data.name) errors.push(t('ontology:template.validation.nameRequired'));
    if (!data.industry) errors.push(t('ontology:template.validation.industryRequired'));
    if (!data.version) warnings.push(t('ontology:template.validation.versionMissing'));

    // Entity types validation
    if (!data.entity_types || !Array.isArray(data.entity_types)) {
      warnings.push(t('ontology:template.validation.noEntityTypes'));
    } else {
      const entityTypes = data.entity_types as Array<Record<string, unknown>>;
      entityTypes.forEach((et, index) => {
        if (!et.id) errors.push(t('ontology:template.validation.entityIdMissing', { index }));
        if (!et.name) errors.push(t('ontology:template.validation.entityNameMissing', { index }));
      });
    }

    // Relation types validation
    if (!data.relation_types || !Array.isArray(data.relation_types)) {
      warnings.push(t('ontology:template.validation.noRelationTypes'));
    } else {
      const relationTypes = data.relation_types as Array<Record<string, unknown>>;
      relationTypes.forEach((rt, index) => {
        if (!rt.id) errors.push(t('ontology:template.validation.relationIdMissing', { index }));
        if (!rt.name) errors.push(t('ontology:template.validation.relationNameMissing', { index }));
        if (!rt.source_type) errors.push(t('ontology:template.validation.sourceTypeMissing', { index }));
        if (!rt.target_type) errors.push(t('ontology:template.validation.targetTypeMissing', { index }));
      });
    }

    return { errors, warnings };
  };

  // Parse file content
  const parseFileContent = useCallback(async (file: File): Promise<Record<string, unknown> | null> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          let data: Record<string, unknown>;

          if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
            // For YAML, we'd need a YAML parser library
            // For now, we'll show an error suggesting JSON
            setParseError(t('ontology:template.yamlNotSupported'));
            resolve(null);
            return;
          } else {
            data = JSON.parse(content);
          }

          resolve(data);
        } catch (err) {
          setParseError(t('ontology:template.parseError'));
          resolve(null);
        }
      };
      reader.onerror = () => {
        setParseError(t('ontology:template.readError'));
        resolve(null);
      };
      reader.readAsText(file);
    });
  }, [t]);

  // Handle file upload
  const handleFileChange: UploadProps['onChange'] = async ({ fileList: newFileList }) => {
    setFileList(newFileList);
    setParseError(null);
    setImportPreview(null);

    if (newFileList.length > 0 && newFileList[0].originFileObj) {
      const file = newFileList[0].originFileObj;
      const data = await parseFileContent(file);

      if (data) {
        const { errors, warnings } = validateTemplate(data);
        
        // Create preview
        const preview: ImportPreview = {
          template: {
            id: (data.id as string) || `imported-${Date.now()}`,
            name: (data.name as string) || '',
            industry: (data.industry as string) || '',
            version: (data.version as string) || '1.0.0',
            description: data.description as string,
            entity_types: (data.entity_types as OntologyTemplate['entity_types']) || [],
            relation_types: (data.relation_types as OntologyTemplate['relation_types']) || [],
            validation_rules: (data.validation_rules as OntologyTemplate['validation_rules']) || [],
            usage_count: 0,
            lineage: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          validationErrors: errors,
          validationWarnings: warnings,
        };

        setImportPreview(preview);
      }
    }
  };

  // Handle import
  const handleImport = () => {
    if (!importPreview || importPreview.validationErrors.length > 0) return;

    // Convert template to import format
    const templateData: Record<string, unknown> = {
      name: importPreview.template.name,
      industry: importPreview.template.industry,
      version: importPreview.template.version,
      description: importPreview.template.description,
      entity_types: importPreview.template.entity_types,
      relation_types: importPreview.template.relation_types,
      validation_rules: importPreview.template.validation_rules,
    };

    importMutation.mutate(templateData);
  };

  // Render export content
  const renderExportContent = () => (
    <div>
      <Alert
        message={t('ontology:template.exportInfo')}
        description={t('ontology:template.exportInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {template && (
        <Card style={{ marginBottom: 24 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label={t('ontology:template.templateName')}>
              <Text strong>{template.name}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={t('ontology:template.version')}>
              v{template.version}
            </Descriptions.Item>
            <Descriptions.Item label={t('ontology:template.industry')}>
              <Tag color="gold">{template.industry}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('ontology:template.usageCount')}>
              {template.usage_count || 0}
            </Descriptions.Item>
            <Descriptions.Item label={t('ontology:template.entityTypes')}>
              {template.entity_types?.length || 0}
            </Descriptions.Item>
            <Descriptions.Item label={t('ontology:template.relationTypes')}>
              {template.relation_types?.length || 0}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Divider>{t('ontology:template.selectFormat')}</Divider>

      <Radio.Group
        value={exportFormat}
        onChange={(e) => setExportFormat(e.target.value)}
        style={{ marginBottom: 24 }}
      >
        <Space direction="vertical">
          <Radio value="json">
            <Space>
              <FileTextOutlined />
              <Text strong>JSON</Text>
              <Text type="secondary">({t('ontology:template.jsonDesc')})</Text>
            </Space>
          </Radio>
          <Radio value="yaml">
            <Space>
              <FileTextOutlined />
              <Text strong>YAML</Text>
              <Text type="secondary">({t('ontology:template.yamlDesc')})</Text>
            </Space>
          </Radio>
        </Space>
      </Radio.Group>
    </div>
  );

  // Render import content
  const renderImportContent = () => (
    <div>
      <Alert
        message={t('ontology:template.importInfo')}
        description={t('ontology:template.importInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Dragger
        fileList={fileList}
        onChange={handleFileChange}
        beforeUpload={() => false}
        maxCount={1}
        accept=".json,.yaml,.yml"
        style={{ marginBottom: 24 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">{t('ontology:template.dragOrClick')}</p>
        <p className="ant-upload-hint">{t('ontology:template.supportedFormats')}</p>
      </Dragger>

      {parseError && (
        <Alert
          message={t('ontology:template.parseErrorTitle')}
          description={parseError}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      {importPreview && (
        <div>
          <Divider>{t('ontology:template.importPreview')}</Divider>

          {/* Validation Results */}
          {importPreview.validationErrors.length > 0 && (
            <Alert
              message={t('ontology:template.validationErrors')}
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {importPreview.validationErrors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              }
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {importPreview.validationWarnings.length > 0 && (
            <Alert
              message={t('ontology:template.validationWarnings')}
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {importPreview.validationWarnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              }
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {importPreview.validationErrors.length === 0 && (
            <Result
              status="success"
              title={t('ontology:template.validationPassed')}
              subTitle={t('ontology:template.readyToImport')}
              style={{ padding: '16px 0' }}
            />
          )}

          {/* Template Preview */}
          <Card size="small">
            <Descriptions column={2} size="small">
              <Descriptions.Item label={t('ontology:template.templateName')}>
                <Text strong>{importPreview.template.name || '-'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('ontology:template.version')}>
                v{importPreview.template.version || '1.0.0'}
              </Descriptions.Item>
              <Descriptions.Item label={t('ontology:template.industry')}>
                {importPreview.template.industry ? (
                  <Tag color="gold">{importPreview.template.industry}</Tag>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label={t('ontology:template.description')}>
                {importPreview.template.description || '-'}
              </Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: '12px 0' }} />

            <Row gutter={16}>
              <Col span={8}>
                <Space>
                  <NodeIndexOutlined style={{ color: '#52c41a' }} />
                  <Text>
                    {importPreview.template.entity_types?.length || 0}{' '}
                    {t('ontology:template.entityTypes')}
                  </Text>
                </Space>
              </Col>
              <Col span={8}>
                <Space>
                  <BranchesOutlined style={{ color: '#1890ff' }} />
                  <Text>
                    {importPreview.template.relation_types?.length || 0}{' '}
                    {t('ontology:template.relationTypes')}
                  </Text>
                </Space>
              </Col>
              <Col span={8}>
                <Space>
                  <SafetyCertificateOutlined style={{ color: '#faad14' }} />
                  <Text>
                    {importPreview.template.validation_rules?.length || 0}{' '}
                    {t('ontology:template.validationRules')}
                  </Text>
                </Space>
              </Col>
            </Row>
          </Card>
        </div>
      )}
    </div>
  );

  const isExportMode = mode === 'export';

  return (
    <Modal
      title={
        <Space>
          {isExportMode ? <DownloadOutlined /> : <UploadOutlined />}
          {isExportMode
            ? t('ontology:template.exportTitle')
            : t('ontology:template.importTitle')}
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={700}
      footer={
        <Space>
          <Button onClick={handleClose}>{t('common:cancel')}</Button>
          {isExportMode ? (
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exportMutation.isPending}
              disabled={!template}
            >
              {t('ontology:template.export')}
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={handleImport}
              loading={importMutation.isPending}
              disabled={
                !importPreview || importPreview.validationErrors.length > 0
              }
            >
              {t('ontology:template.import')}
            </Button>
          )}
        </Space>
      }
    >
      <Spin spinning={exportMutation.isPending || importMutation.isPending}>
        {isExportMode ? renderExportContent() : renderImportContent()}
      </Spin>
    </Modal>
  );
};

export default TemplateExportImport;
