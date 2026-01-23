/**
 * Configuration Import/Export Page
 *
 * Provides bulk import/export functionality for:
 * - LLM configurations
 * - Database configurations
 * - Sync strategies
 *
 * **Feature: admin-configuration**
 * **Validates: Requirements 9.3**
 */

import React, { useState } from 'react';
import {
  Card, Button, Space, Tag, Upload, message, Row, Col, Checkbox, Divider,
  Alert, Table, Modal, Result, Steps, Typography, Descriptions, Spin
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';
import {
  DownloadOutlined, UploadOutlined, FileTextOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ExclamationCircleOutlined, CloudOutlined,
  DatabaseOutlined, SyncOutlined, EyeOutlined
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

const { Text, Title } = Typography;
const { Dragger } = Upload;

// Types
interface ImportResult {
  config_type: string;
  config_name: string;
  status: string;
  message?: string;
  config_id?: string;
}

interface ImportResponse {
  success: boolean;
  dry_run: boolean;
  total_processed: number;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  results: ImportResult[];
}

interface ExportResponse {
  version: string;
  exported_at: string;
  tenant_id?: string;
  configs: {
    llm?: any[];
    database?: any[];
    sync?: any[];
  };
  metadata: {
    config_counts: Record<string, number>;
    export_options: {
      include_sensitive: boolean;
      config_types: string[];
    };
  };
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// Mock API functions - replace with actual API calls
const exportConfigs = async (options: {
  configTypes: string[];
  includeSensitive: boolean;
}): Promise<ExportResponse> => {
  // Replace with actual API call: GET /api/v1/admin/config-export
  return {
    version: '1.0',
    exported_at: new Date().toISOString(),
    tenant_id: 'default',
    configs: {
      llm: options.configTypes.includes('llm') ? [
        { id: '1', name: 'OpenAI Config', provider: 'openai', api_key: '***REDACTED***' }
      ] : [],
      database: options.configTypes.includes('database') ? [
        { id: '2', name: 'Primary DB', db_type: 'postgresql', host: 'localhost', password: '***REDACTED***' }
      ] : [],
      sync: options.configTypes.includes('sync') ? [
        { id: '3', name: 'CRM Sync', db_config_id: '2', sync_mode: 'poll' }
      ] : [],
    },
    metadata: {
      config_counts: {
        llm: 1,
        database: 1,
        sync: 1,
      },
      export_options: {
        include_sensitive: options.includeSensitive,
        config_types: options.configTypes,
      },
    },
  };
};

const importConfigs = async (data: {
  configs: any;
  overwriteExisting: boolean;
  dryRun: boolean;
}): Promise<ImportResponse> => {
  // Replace with actual API call: POST /api/v1/admin/config-import
  const results: ImportResult[] = [];
  let created = 0, updated = 0, skipped = 0, errors = 0;

  for (const [type, configs] of Object.entries(data.configs)) {
    if (Array.isArray(configs)) {
      for (const config of configs) {
        if (config.api_key?.includes('REDACTED') || config.password?.includes('REDACTED')) {
          results.push({
            config_type: type,
            config_name: config.name || 'Unknown',
            status: 'error',
            message: 'Cannot import config with redacted values',
          });
          errors++;
        } else {
          results.push({
            config_type: type,
            config_name: config.name || 'Unknown',
            status: data.dryRun ? 'would_be_created' : 'created',
            config_id: config.id,
          });
          created++;
        }
      }
    }
  }

  return {
    success: errors === 0,
    dry_run: data.dryRun,
    total_processed: results.length,
    created,
    updated,
    skipped,
    errors,
    results,
  };
};

const validateImport = async (data: any): Promise<ValidationResult> => {
  // Replace with actual API call: POST /api/v1/admin/config-import/validate
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!data.version) {
    errors.push('Missing version field');
  }

  if (!data.configs) {
    errors.push('Missing configs field');
  }

  if (JSON.stringify(data).includes('REDACTED')) {
    warnings.push('File contains redacted values - these cannot be imported');
  }

  return { valid: errors.length === 0, errors, warnings };
};

const ConfigImportExport: React.FC = () => {
  const { t } = useTranslation('admin');
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['llm', 'database', 'sync']);
  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [importFile, setImportFile] = useState<any>(null);
  const [importData, setImportData] = useState<any>(null);
  const [importStep, setImportStep] = useState(0);
  const [overwriteExisting, setOverwriteExisting] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [exportData, setExportData] = useState<ExportResponse | null>(null);
  const [importResults, setImportResults] = useState<ImportResponse | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: exportConfigs,
    onSuccess: (data) => {
      setExportData(data);
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `config-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success(t('importExport.exportSuccess', 'Configuration exported successfully'));
    },
    onError: (error: any) => {
      message.error(error.message || t('importExport.exportFailed', 'Export failed'));
    },
  });

  // Validate mutation
  const validateMutation = useMutation({
    mutationFn: validateImport,
    onSuccess: (result) => {
      setValidationResult(result);
      if (result.valid) {
        setImportStep(1);
      }
    },
    onError: (error: any) => {
      message.error(error.message || t('importExport.validationFailed', 'Validation failed'));
    },
  });

  // Import mutation (dry run)
  const dryRunMutation = useMutation({
    mutationFn: (data: any) => importConfigs({ configs: data.configs, overwriteExisting, dryRun: true }),
    onSuccess: (result) => {
      setImportResults(result);
      setImportStep(2);
    },
    onError: (error: any) => {
      message.error(error.message || t('importExport.dryRunFailed', 'Dry run failed'));
    },
  });

  // Import mutation (actual)
  const importMutation = useMutation({
    mutationFn: (data: any) => importConfigs({ configs: data.configs, overwriteExisting, dryRun: false }),
    onSuccess: (result) => {
      setImportResults(result);
      setImportStep(3);
      if (result.success) {
        message.success(t('importExport.importSuccess', 'Configuration imported successfully'));
      } else {
        message.warning(t('importExport.importPartial', 'Import completed with errors'));
      }
    },
    onError: (error: any) => {
      message.error(error.message || t('importExport.importFailed', 'Import failed'));
    },
  });

  const handleExport = () => {
    if (selectedTypes.length === 0) {
      message.warning(t('importExport.selectTypes', 'Please select at least one config type'));
      return;
    }
    exportMutation.mutate({ configTypes: selectedTypes, includeSensitive });
  };

  const handleFileUpload = (file: any) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        setImportData(data);
        setImportFile(file);
        setImportStep(0);
        setValidationResult(null);
        setImportResults(null);
        setImportModalVisible(true);
        // Auto-validate
        validateMutation.mutate(data);
      } catch {
        message.error(t('importExport.invalidJson', 'Invalid JSON file'));
      }
    };
    reader.readAsText(file);
    return false; // Prevent upload
  };

  const handleDryRun = () => {
    if (importData) {
      dryRunMutation.mutate(importData);
    }
  };

  const handleImport = () => {
    if (importData) {
      importMutation.mutate(importData);
    }
  };

  const resetImport = () => {
    setImportData(null);
    setImportFile(null);
    setImportStep(0);
    setValidationResult(null);
    setImportResults(null);
    setImportModalVisible(false);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.json',
    showUploadList: false,
    beforeUpload: handleFileUpload,
  };

  const resultColumns: ColumnsType<ImportResult> = [
    {
      title: t('importExport.columns.type', 'Type'),
      dataIndex: 'config_type',
      key: 'type',
      width: 100,
      render: (type) => {
        const icons: Record<string, React.ReactNode> = {
          llm: <CloudOutlined />,
          database: <DatabaseOutlined />,
          sync: <SyncOutlined />,
        };
        return (
          <Space>
            {icons[type]}
            {type}
          </Space>
        );
      },
    },
    {
      title: t('importExport.columns.name', 'Name'),
      dataIndex: 'config_name',
      key: 'name',
    },
    {
      title: t('importExport.columns.status', 'Status'),
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status) => {
        const colors: Record<string, string> = {
          created: 'success',
          updated: 'processing',
          skipped: 'warning',
          error: 'error',
          would_be_created: 'blue',
          would_be_updated: 'cyan',
        };
        const icons: Record<string, React.ReactNode> = {
          created: <CheckCircleOutlined />,
          updated: <CheckCircleOutlined />,
          skipped: <ExclamationCircleOutlined />,
          error: <CloseCircleOutlined />,
          would_be_created: <CheckCircleOutlined />,
          would_be_updated: <CheckCircleOutlined />,
        };
        return (
          <Tag color={colors[status]} icon={icons[status]}>
            {status.replace(/_/g, ' ').toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: t('importExport.columns.message', 'Message'),
      dataIndex: 'message',
      key: 'message',
      render: (message) => message ? <Text type="danger">{message}</Text> : '-',
    },
  ];

  const getConfigCount = (data: any) => {
    if (!data?.configs) return 0;
    return Object.values(data.configs).reduce((sum: number, configs: any) => {
      return sum + (Array.isArray(configs) ? configs.length : 0);
    }, 0);
  };

  return (
    <div className="config-import-export">
      <Row gutter={16}>
        {/* Export Section */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <DownloadOutlined />
                {t('importExport.export', 'Export Configuration')}
              </Space>
            }
          >
            <Alert
              message={t('importExport.exportInfo', 'Export configurations for backup or migration')}
              description={t(
                'importExport.exportDescription',
                'Select configuration types to export. Sensitive data (API keys, passwords) are redacted by default.'
              )}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <div style={{ marginBottom: 16 }}>
              <Text strong>{t('importExport.selectTypes', 'Select Configuration Types')}</Text>
              <div style={{ marginTop: 8 }}>
                <Checkbox.Group
                  value={selectedTypes}
                  onChange={(values) => setSelectedTypes(values as string[])}
                  options={[
                    { label: <Space><CloudOutlined /> LLM</Space>, value: 'llm' },
                    { label: <Space><DatabaseOutlined /> Database</Space>, value: 'database' },
                    { label: <Space><SyncOutlined /> Sync</Space>, value: 'sync' },
                  ]}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Checkbox
                checked={includeSensitive}
                onChange={(e) => setIncludeSensitive(e.target.checked)}
              >
                <Space>
                  {t('importExport.includeSensitive', 'Include sensitive data')}
                  <Text type="danger">({t('importExport.notRecommended', 'Not recommended')})</Text>
                </Space>
              </Checkbox>
            </div>

            {includeSensitive && (
              <Alert
                message={t('importExport.sensitiveWarning', 'Security Warning')}
                description={t(
                  'importExport.sensitiveWarningDesc',
                  'Exported file will contain API keys and passwords. Handle with care.'
                )}
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exportMutation.isPending}
              disabled={selectedTypes.length === 0}
              block
            >
              {t('importExport.exportButton', 'Export Configuration')}
            </Button>
          </Card>
        </Col>

        {/* Import Section */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <UploadOutlined />
                {t('importExport.import', 'Import Configuration')}
              </Space>
            }
          >
            <Alert
              message={t('importExport.importInfo', 'Import configurations from a backup file')}
              description={t(
                'importExport.importDescription',
                'Upload a JSON file previously exported. Files with redacted sensitive data cannot be imported.'
              )}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
              <p className="ant-upload-drag-icon">
                <FileTextOutlined />
              </p>
              <p className="ant-upload-text">
                {t('importExport.dropFile', 'Click or drag file to this area')}
              </p>
              <p className="ant-upload-hint">
                {t('importExport.supportedFormat', 'Supports JSON format exported from this system')}
              </p>
            </Dragger>

            <div style={{ marginBottom: 16 }}>
              <Checkbox
                checked={overwriteExisting}
                onChange={(e) => setOverwriteExisting(e.target.checked)}
              >
                {t('importExport.overwriteExisting', 'Overwrite existing configurations')}
              </Checkbox>
            </div>

            {exportData && (
              <Button
                icon={<EyeOutlined />}
                onClick={() => setPreviewModalVisible(true)}
                block
              >
                {t('importExport.previewLastExport', 'Preview Last Export')}
              </Button>
            )}
          </Card>
        </Col>
      </Row>

      {/* Import Modal */}
      <Modal
        title={t('importExport.importWizard', 'Import Configuration Wizard')}
        open={importModalVisible}
        onCancel={resetImport}
        footer={null}
        width={800}
      >
        <Steps
          current={importStep}
          items={[
            { title: t('importExport.step.validate', 'Validate') },
            { title: t('importExport.step.preview', 'Preview') },
            { title: t('importExport.step.import', 'Import') },
            { title: t('importExport.step.complete', 'Complete') },
          ]}
          style={{ marginBottom: 24 }}
        />

        {/* Step 0: Validation */}
        {importStep === 0 && (
          <div>
            <Spin spinning={validateMutation.isPending}>
              {validationResult && (
                <>
                  {validationResult.valid ? (
                    <Alert
                      message={t('importExport.validationSuccess', 'Validation Passed')}
                      type="success"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  ) : (
                    <Alert
                      message={t('importExport.validationFailed', 'Validation Failed')}
                      description={
                        <ul>
                          {validationResult.errors.map((err, i) => (
                            <li key={i}><Text type="danger">{err}</Text></li>
                          ))}
                        </ul>
                      }
                      type="error"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  {validationResult.warnings.length > 0 && (
                    <Alert
                      message={t('importExport.warnings', 'Warnings')}
                      description={
                        <ul>
                          {validationResult.warnings.map((warn, i) => (
                            <li key={i}><Text type="warning">{warn}</Text></li>
                          ))}
                        </ul>
                      }
                      type="warning"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                </>
              )}
              {importData && (
                <Descriptions bordered size="small" column={2}>
                  <Descriptions.Item label={t('importExport.version', 'Version')}>
                    {importData.version}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('importExport.totalConfigs', 'Total Configs')}>
                    {getConfigCount(importData)}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('importExport.llmConfigs', 'LLM Configs')}>
                    {importData.configs?.llm?.length || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('importExport.dbConfigs', 'Database Configs')}>
                    {importData.configs?.database?.length || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('importExport.syncConfigs', 'Sync Configs')}>
                    {importData.configs?.sync?.length || 0}
                  </Descriptions.Item>
                </Descriptions>
              )}
            </Spin>
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Space>
                <Button onClick={resetImport}>{t('importExport.cancel', 'Cancel')}</Button>
                <Button
                  type="primary"
                  onClick={handleDryRun}
                  disabled={!validationResult?.valid}
                  loading={dryRunMutation.isPending}
                >
                  {t('importExport.continue', 'Continue')}
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* Step 1: Preview */}
        {importStep === 1 && (
          <div>
            <Spin spinning={dryRunMutation.isPending}>
              <Alert
                message={t('importExport.dryRunInfo', 'Dry Run Preview')}
                description={t('importExport.dryRunDesc', 'Review the changes that will be made before importing.')}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            </Spin>
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setImportStep(0)}>{t('importExport.back', 'Back')}</Button>
                <Button
                  type="primary"
                  onClick={handleDryRun}
                  loading={dryRunMutation.isPending}
                >
                  {t('importExport.runPreview', 'Run Preview')}
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* Step 2: Import */}
        {importStep === 2 && importResults && (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title={t('importExport.willCreate', 'Will Create')}
                    value={importResults.created}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title={t('importExport.willUpdate', 'Will Update')}
                    value={importResults.updated}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title={t('importExport.willSkip', 'Will Skip')}
                    value={importResults.skipped}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title={t('importExport.errors', 'Errors')}
                    value={importResults.errors}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
            </Row>

            <Table
              columns={resultColumns}
              dataSource={importResults.results}
              rowKey={(record, index) => `${record.config_type}-${index}`}
              size="small"
              pagination={false}
              scroll={{ y: 300 }}
            />

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Space>
                <Button onClick={resetImport}>{t('importExport.cancel', 'Cancel')}</Button>
                <Button
                  type="primary"
                  onClick={handleImport}
                  loading={importMutation.isPending}
                  disabled={importResults.errors > 0 && importResults.created === 0}
                >
                  {t('importExport.confirmImport', 'Confirm Import')}
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* Step 3: Complete */}
        {importStep === 3 && importResults && (
          <Result
            status={importResults.success ? 'success' : 'warning'}
            title={importResults.success
              ? t('importExport.importComplete', 'Import Complete')
              : t('importExport.importPartialComplete', 'Import Completed with Issues')
            }
            subTitle={
              <Space direction="vertical">
                <Text>
                  {t('importExport.processedCount', 'Processed: {{count}}', { count: importResults.total_processed })}
                </Text>
                <Space>
                  <Tag color="success">{importResults.created} {t('importExport.created', 'created')}</Tag>
                  <Tag color="blue">{importResults.updated} {t('importExport.updated', 'updated')}</Tag>
                  <Tag color="warning">{importResults.skipped} {t('importExport.skipped', 'skipped')}</Tag>
                  <Tag color="error">{importResults.errors} {t('importExport.failed', 'failed')}</Tag>
                </Space>
              </Space>
            }
            extra={[
              <Button key="close" type="primary" onClick={resetImport}>
                {t('importExport.close', 'Close')}
              </Button>,
            ]}
          />
        )}
      </Modal>

      {/* Preview Modal */}
      <Modal
        title={t('importExport.exportPreview', 'Export Preview')}
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            {t('importExport.close', 'Close')}
          </Button>,
        ]}
        width={800}
      >
        {exportData && (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label={t('importExport.version', 'Version')}>
                {exportData.version}
              </Descriptions.Item>
              <Descriptions.Item label={t('importExport.exportedAt', 'Exported At')}>
                {new Date(exportData.exported_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('importExport.llmConfigs', 'LLM Configs')}>
                {exportData.metadata.config_counts.llm || 0}
              </Descriptions.Item>
              <Descriptions.Item label={t('importExport.dbConfigs', 'Database Configs')}>
                {exportData.metadata.config_counts.database || 0}
              </Descriptions.Item>
              <Descriptions.Item label={t('importExport.syncConfigs', 'Sync Configs')}>
                {exportData.metadata.config_counts.sync || 0}
              </Descriptions.Item>
              <Descriptions.Item label={t('importExport.includedSensitive', 'Included Sensitive')}>
                {exportData.metadata.export_options.include_sensitive ? 'Yes' : 'No'}
              </Descriptions.Item>
            </Descriptions>
            <pre style={{
              backgroundColor: '#f5f5f5',
              padding: 12,
              borderRadius: 4,
              maxHeight: 400,
              overflow: 'auto',
              fontSize: 12,
            }}>
              {JSON.stringify(exportData, null, 2)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ConfigImportExport;
