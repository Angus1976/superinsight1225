/**
 * Export Options Modal Component
 * Allows users to configure export settings including format, fields, and range
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Modal,
  Form,
  Radio,
  Checkbox,
  Space,
  Button,
  Divider,
  Typography,
  List,
  Tag,
  Tooltip,
  Alert,
  Collapse,
  Empty,
} from 'antd';
import {
  FileTextOutlined,
  FileExcelOutlined,
  CodeOutlined,
  DownloadOutlined,
  HistoryOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Task } from '@/types';

const { Text, Title } = Typography;
const { Panel } = Collapse;

/**
 * Export format types
 */
export type ExportFormat = 'csv' | 'json' | 'excel';

/**
 * Export range types
 */
export type ExportRange = 'all' | 'selected' | 'filtered';

/**
 * Available export fields
 */
export type ExportField = 
  | 'id'
  | 'name'
  | 'description'
  | 'status'
  | 'priority'
  | 'annotation_type'
  | 'progress'
  | 'completed_items'
  | 'total_items'
  | 'assignee_name'
  | 'created_at'
  | 'due_date'
  | 'label_studio_project_id'
  | 'label_studio_sync_status'
  | 'tags';

/**
 * Export history entry
 */
export interface ExportHistoryEntry {
  id: string;
  timestamp: string;
  format: ExportFormat;
  range: ExportRange;
  taskCount: number;
  fields: ExportField[];
  filename: string;
}

/**
 * Export options configuration
 */
export interface ExportOptions {
  format: ExportFormat;
  range: ExportRange;
  fields: ExportField[];
  includeAnnotations?: boolean;
  includeProjectConfig?: boolean;
  includeSyncMetadata?: boolean;
}

/**
 * Props for ExportOptionsModal
 */
export interface ExportOptionsModalProps {
  open: boolean;
  onCancel: () => void;
  onExport: (options: ExportOptions) => void;
  selectedCount: number;
  filteredCount: number;
  totalCount: number;
  loading?: boolean;
}

// Local storage key for export history
const EXPORT_HISTORY_KEY = 'superinsight_export_history';
const MAX_HISTORY_ENTRIES = 10;

/**
 * Default export fields
 */
const DEFAULT_FIELDS: ExportField[] = [
  'id',
  'name',
  'status',
  'priority',
  'annotation_type',
  'progress',
  'completed_items',
  'total_items',
  'assignee_name',
  'created_at',
  'due_date',
];

/**
 * All available export fields
 */
const ALL_FIELDS: ExportField[] = [
  'id',
  'name',
  'description',
  'status',
  'priority',
  'annotation_type',
  'progress',
  'completed_items',
  'total_items',
  'assignee_name',
  'created_at',
  'due_date',
  'label_studio_project_id',
  'label_studio_sync_status',
  'tags',
];

/**
 * Get export history from localStorage
 */
const getExportHistory = (): ExportHistoryEntry[] => {
  try {
    const stored = localStorage.getItem(EXPORT_HISTORY_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to load export history:', error);
  }
  return [];
};

/**
 * Save export history to localStorage
 */
const saveExportHistory = (history: ExportHistoryEntry[]): void => {
  try {
    localStorage.setItem(EXPORT_HISTORY_KEY, JSON.stringify(history));
  } catch (error) {
    console.error('Failed to save export history:', error);
  }
};

/**
 * Add entry to export history
 */
export const addExportHistoryEntry = (entry: Omit<ExportHistoryEntry, 'id' | 'timestamp'>): void => {
  const history = getExportHistory();
  const newEntry: ExportHistoryEntry = {
    ...entry,
    id: `export_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
  };
  
  // Add to beginning and limit to max entries
  const updatedHistory = [newEntry, ...history].slice(0, MAX_HISTORY_ENTRIES);
  saveExportHistory(updatedHistory);
};

/**
 * Clear export history
 */
const clearExportHistory = (): void => {
  localStorage.removeItem(EXPORT_HISTORY_KEY);
};

/**
 * Export Options Modal Component
 */
export const ExportOptionsModal: React.FC<ExportOptionsModalProps> = ({
  open,
  onCancel,
  onExport,
  selectedCount,
  filteredCount,
  totalCount,
  loading = false,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const [form] = Form.useForm();
  
  // State
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [range, setRange] = useState<ExportRange>('all');
  const [selectedFields, setSelectedFields] = useState<ExportField[]>(DEFAULT_FIELDS);
  const [includeAnnotations, setIncludeAnnotations] = useState(true);
  const [includeProjectConfig, setIncludeProjectConfig] = useState(true);
  const [includeSyncMetadata, setIncludeSyncMetadata] = useState(true);
  const [exportHistory, setExportHistory] = useState<ExportHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Load export history on mount
  useEffect(() => {
    if (open) {
      setExportHistory(getExportHistory());
    }
  }, [open]);

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setFormat('csv');
      setRange(selectedCount > 0 ? 'selected' : 'all');
      setSelectedFields(DEFAULT_FIELDS);
      setIncludeAnnotations(true);
      setIncludeProjectConfig(true);
      setIncludeSyncMetadata(true);
    }
  }, [open, selectedCount]);

  // Get task count based on range
  const getTaskCount = useCallback((): number => {
    switch (range) {
      case 'selected':
        return selectedCount;
      case 'filtered':
        return filteredCount;
      case 'all':
      default:
        return totalCount;
    }
  }, [range, selectedCount, filteredCount, totalCount]);

  // Handle export
  const handleExport = useCallback(() => {
    const options: ExportOptions = {
      format,
      range,
      fields: selectedFields,
      includeAnnotations: format === 'json' ? includeAnnotations : undefined,
      includeProjectConfig: format === 'json' ? includeProjectConfig : undefined,
      includeSyncMetadata: format === 'json' ? includeSyncMetadata : undefined,
    };
    
    onExport(options);
  }, [format, range, selectedFields, includeAnnotations, includeProjectConfig, includeSyncMetadata, onExport]);

  // Handle field selection
  const handleFieldChange = useCallback((field: ExportField, checked: boolean) => {
    setSelectedFields(prev => {
      if (checked) {
        return [...prev, field];
      }
      return prev.filter(f => f !== field);
    });
  }, []);

  // Select all fields
  const handleSelectAllFields = useCallback(() => {
    setSelectedFields([...ALL_FIELDS]);
  }, []);

  // Deselect all fields
  const handleDeselectAllFields = useCallback(() => {
    setSelectedFields([]);
  }, []);

  // Reset to default fields
  const handleResetFields = useCallback(() => {
    setSelectedFields([...DEFAULT_FIELDS]);
  }, []);

  // Delete history entry
  const handleDeleteHistoryEntry = useCallback((id: string) => {
    const history = getExportHistory();
    const updatedHistory = history.filter(entry => entry.id !== id);
    saveExportHistory(updatedHistory);
    setExportHistory(updatedHistory);
  }, []);

  // Clear all history
  const handleClearHistory = useCallback(() => {
    clearExportHistory();
    setExportHistory([]);
  }, []);

  // Apply history entry settings
  const handleApplyHistoryEntry = useCallback((entry: ExportHistoryEntry) => {
    setFormat(entry.format);
    setRange(entry.range);
    setSelectedFields(entry.fields);
    setShowHistory(false);
  }, []);

  // Format icon
  const getFormatIcon = (fmt: ExportFormat) => {
    switch (fmt) {
      case 'csv':
        return <FileTextOutlined />;
      case 'json':
        return <CodeOutlined />;
      case 'excel':
        return <FileExcelOutlined />;
    }
  };

  // Format relative time
  const formatRelativeTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / (1000 * 60));
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffMin < 1) {
      return t('syncTimeJustNow');
    } else if (diffMin < 60) {
      return t('syncTimeMinutesAgo', { count: diffMin });
    } else if (diffHour < 24) {
      return t('syncTimeHoursAgo', { count: diffHour });
    } else {
      return t('syncTimeDaysAgo', { count: diffDay });
    }
  };

  // Field label mapping
  const getFieldLabel = (field: ExportField): string => {
    const fieldLabels: Record<ExportField, string> = {
      id: t('columns.id'),
      name: t('columns.name'),
      description: t('description'),
      status: t('columns.status'),
      priority: t('columns.priority'),
      annotation_type: t('columns.annotationType'),
      progress: t('columns.progress'),
      completed_items: t('columns.completedItems'),
      total_items: t('columns.totalItems'),
      assignee_name: t('columns.assignee'),
      created_at: t('columns.createdAt'),
      due_date: t('columns.dueDate'),
      label_studio_project_id: t('detail.projectId'),
      label_studio_sync_status: t('syncStatus'),
      tags: t('tagsLabel'),
    };
    return fieldLabels[field] || field;
  };

  // Memoized field groups
  const fieldGroups = useMemo(() => ({
    basic: ['id', 'name', 'description', 'status', 'priority', 'annotation_type'] as ExportField[],
    progress: ['progress', 'completed_items', 'total_items'] as ExportField[],
    assignment: ['assignee_name', 'created_at', 'due_date'] as ExportField[],
    labelStudio: ['label_studio_project_id', 'label_studio_sync_status', 'tags'] as ExportField[],
  }), []);

  return (
    <Modal
      title={
        <Space>
          <DownloadOutlined />
          {t('export.title')}
        </Space>
      }
      open={open}
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="history" icon={<HistoryOutlined />} onClick={() => setShowHistory(!showHistory)}>
          {t('export.history')}
        </Button>,
        <Button key="cancel" onClick={onCancel}>
          {t('cancel')}
        </Button>,
        <Button
          key="export"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleExport}
          loading={loading}
          disabled={selectedFields.length === 0 || getTaskCount() === 0}
        >
          {t('export.exportButton')} ({getTaskCount()})
        </Button>,
      ]}
    >
      {/* Export History Panel */}
      {showHistory && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Title level={5} style={{ margin: 0 }}>
              <HistoryOutlined /> {t('export.exportHistory') || 'Export History'}
            </Title>
            {exportHistory.length > 0 && (
              <Button 
                type="link" 
                danger 
                size="small" 
                onClick={handleClearHistory}
              >
                {t('export.clearHistory') || 'Clear All'}
              </Button>
            )}
          </div>
          
          {exportHistory.length === 0 ? (
            <Empty 
              description={t('export.noHistory') || 'No export history'} 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <List
              size="small"
              dataSource={exportHistory}
              style={{ maxHeight: 200, overflow: 'auto' }}
              renderItem={(entry) => (
                <List.Item
                  actions={[
                    <Tooltip title={t('export.applySettings') || 'Apply Settings'} key="apply">
                      <Button 
                        type="link" 
                        size="small"
                        onClick={() => handleApplyHistoryEntry(entry)}
                      >
                        {t('export.apply') || 'Apply'}
                      </Button>
                    </Tooltip>,
                    <Tooltip title={t('delete')} key="delete">
                      <Button 
                        type="link" 
                        danger 
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => handleDeleteHistoryEntry(entry.id)}
                      />
                    </Tooltip>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={getFormatIcon(entry.format)}
                    title={
                      <Space>
                        <Tag color={entry.format === 'csv' ? 'blue' : entry.format === 'json' ? 'green' : 'orange'}>
                          {entry.format.toUpperCase()}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {entry.taskCount} {t('export.tasks') || 'tasks'}
                        </Text>
                      </Space>
                    }
                    description={
                      <Space size={4}>
                        <ClockCircleOutlined />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {formatRelativeTime(entry.timestamp)}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
          <Divider style={{ margin: '12px 0' }} />
        </div>
      )}

      {/* Export Format Selection */}
      <div style={{ marginBottom: 24 }}>
        <Title level={5}>{t('export.selectFormat')}</Title>
        <Radio.Group 
          value={format} 
          onChange={(e) => setFormat(e.target.value)}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Radio value="csv" style={{ width: '100%' }}>
              <Space>
                <FileTextOutlined style={{ color: '#1890ff' }} />
                <span>{t('export.csv')}</span>
              </Space>
              <Text type="secondary" style={{ display: 'block', marginLeft: 24, fontSize: 12 }}>
                {t('export.csvDescription') || 'Simple tabular format, compatible with spreadsheet applications'}
              </Text>
            </Radio>
            <Radio value="json" style={{ width: '100%' }}>
              <Space>
                <CodeOutlined style={{ color: '#52c41a' }} />
                <span>{t('export.json')}</span>
              </Space>
              <Text type="secondary" style={{ display: 'block', marginLeft: 24, fontSize: 12 }}>
                {t('export.jsonDescription') || 'Complete data with annotations and metadata'}
              </Text>
            </Radio>
            <Radio value="excel" style={{ width: '100%' }}>
              <Space>
                <FileExcelOutlined style={{ color: '#fa8c16' }} />
                <span>{t('export.excelFormat')}</span>
              </Space>
              <Text type="secondary" style={{ display: 'block', marginLeft: 24, fontSize: 12 }}>
                {t('export.excelDescription') || 'Multi-sheet workbook with summary and charts data'}
              </Text>
            </Radio>
          </Space>
        </Radio.Group>
      </div>

      {/* JSON-specific options */}
      {format === 'json' && (
        <div style={{ marginBottom: 24 }}>
          <Title level={5}>{t('export.jsonOptions') || 'JSON Options'}</Title>
          <Space direction="vertical">
            <Checkbox 
              checked={includeAnnotations} 
              onChange={(e) => setIncludeAnnotations(e.target.checked)}
            >
              {t('export.includeAnnotations')}
            </Checkbox>
            <Checkbox 
              checked={includeProjectConfig} 
              onChange={(e) => setIncludeProjectConfig(e.target.checked)}
            >
              {t('export.includeProjectConfig')}
            </Checkbox>
            <Checkbox 
              checked={includeSyncMetadata} 
              onChange={(e) => setIncludeSyncMetadata(e.target.checked)}
            >
              {t('export.includeSyncMetadata')}
            </Checkbox>
          </Space>
        </div>
      )}

      {/* Export Range Selection */}
      <div style={{ marginBottom: 24 }}>
        <Title level={5}>{t('export.selectRange') || 'Export Range'}</Title>
        <Radio.Group 
          value={range} 
          onChange={(e) => setRange(e.target.value)}
        >
          <Space direction="vertical">
            <Radio value="all" disabled={totalCount === 0}>
              {t('export.allTasks') || 'All Tasks'} ({totalCount})
            </Radio>
            <Radio value="selected" disabled={selectedCount === 0}>
              {t('export.selectedTasks') || 'Selected Tasks'} ({selectedCount})
              {selectedCount === 0 && (
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  ({t('export.noSelection') || 'No tasks selected'})
                </Text>
              )}
            </Radio>
            <Radio value="filtered" disabled={filteredCount === 0 || filteredCount === totalCount}>
              {t('export.filteredTasks') || 'Filtered Tasks'} ({filteredCount})
              {filteredCount === totalCount && (
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  ({t('export.noFilter') || 'No filter applied'})
                </Text>
              )}
            </Radio>
          </Space>
        </Radio.Group>
      </div>

      {/* Field Selection */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Title level={5} style={{ margin: 0 }}>{t('export.selectFields') || 'Select Fields'}</Title>
          <Space>
            <Button type="link" size="small" onClick={handleSelectAllFields}>
              {t('selectAll')}
            </Button>
            <Button type="link" size="small" onClick={handleDeselectAllFields}>
              {t('selectNone')}
            </Button>
            <Button type="link" size="small" onClick={handleResetFields}>
              {t('export.resetDefault') || 'Reset Default'}
            </Button>
          </Space>
        </div>
        
        <Collapse defaultActiveKey={['basic', 'progress']} ghost>
          <Panel 
            header={t('export.basicFields') || 'Basic Information'} 
            key="basic"
          >
            <Space wrap>
              {fieldGroups.basic.map(field => (
                <Checkbox
                  key={field}
                  checked={selectedFields.includes(field)}
                  onChange={(e) => handleFieldChange(field, e.target.checked)}
                >
                  {getFieldLabel(field)}
                </Checkbox>
              ))}
            </Space>
          </Panel>
          
          <Panel 
            header={t('export.progressFields') || 'Progress Information'} 
            key="progress"
          >
            <Space wrap>
              {fieldGroups.progress.map(field => (
                <Checkbox
                  key={field}
                  checked={selectedFields.includes(field)}
                  onChange={(e) => handleFieldChange(field, e.target.checked)}
                >
                  {getFieldLabel(field)}
                </Checkbox>
              ))}
            </Space>
          </Panel>
          
          <Panel 
            header={t('export.assignmentFields') || 'Assignment Information'} 
            key="assignment"
          >
            <Space wrap>
              {fieldGroups.assignment.map(field => (
                <Checkbox
                  key={field}
                  checked={selectedFields.includes(field)}
                  onChange={(e) => handleFieldChange(field, e.target.checked)}
                >
                  {getFieldLabel(field)}
                </Checkbox>
              ))}
            </Space>
          </Panel>
          
          <Panel 
            header={t('export.labelStudioFields') || 'Label Studio Information'} 
            key="labelStudio"
          >
            <Space wrap>
              {fieldGroups.labelStudio.map(field => (
                <Checkbox
                  key={field}
                  checked={selectedFields.includes(field)}
                  onChange={(e) => handleFieldChange(field, e.target.checked)}
                >
                  {getFieldLabel(field)}
                </Checkbox>
              ))}
            </Space>
          </Panel>
        </Collapse>
      </div>

      {/* Warning for no fields selected */}
      {selectedFields.length === 0 && (
        <Alert
          type="warning"
          message={t('export.noFieldsWarning') || 'Please select at least one field to export'}
          showIcon
        />
      )}

      {/* Info about selected count */}
      {getTaskCount() > 0 && selectedFields.length > 0 && (
        <Alert
          type="info"
          message={
            t('export.exportSummary', { 
              count: getTaskCount(), 
              fields: selectedFields.length,
              format: format.toUpperCase()
            }) || `Will export ${getTaskCount()} tasks with ${selectedFields.length} fields as ${format.toUpperCase()}`
          }
          showIcon
          icon={<CheckCircleOutlined />}
        />
      )}
    </Modal>
  );
};

export default ExportOptionsModal;
