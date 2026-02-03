// Task import modal component
// Features:
// - Import tasks from CSV, JSON, Excel files
// - Preview imported data before confirmation
// - Download template files
// - Permission-based access control
import { 
  Modal, 
  Upload, 
  Button, 
  Space, 
  Table, 
  Alert, 
  Typography,
  Tag,
  Divider,
  App
} from 'antd';
import { useState, useCallback } from 'react';
import { 
  UploadOutlined, 
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useCreateTask } from '@/hooks/useTask';
import { 
  importTasksFromFile, 
  downloadCSVTemplate,
  type ImportResult,
  type ImportedTaskData 
} from '@/utils/import';
import type { CreateTaskPayload } from '@/types';

const { Text, Title } = Typography;
const { Dragger } = Upload;

interface TaskImportModalProps {
  open: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

export const TaskImportModal: React.FC<TaskImportModalProps> = ({
  open,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const { message } = App.useApp();
  const createTask = useCreateTask();
  
  const [importResult, setImportResult] = useState<ImportResult<ImportedTaskData> | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Handle file import
  const handleFileImport = useCallback(async (file: File) => {
    setIsImporting(true);
    try {
      const result = await importTasksFromFile(file, { t });
      setImportResult(result);
      
      if (result.success && result.data.length > 0) {
        message.success(t('import.importSuccess', { count: result.data.length }));
      } else if (result.errors.length > 0) {
        message.warning(t('import.importFailed'));
      }
    } catch (error) {
      message.error(t('import.importFailed'));
    } finally {
      setIsImporting(false);
    }
    return false; // Prevent default upload behavior
  }, [t, message]);

  // Handle download template
  const handleDownloadTemplate = useCallback(() => {
    downloadCSVTemplate(t);
    message.success(t('import.downloadTemplate'));
  }, [t, message]);

  // Handle confirm import - create tasks
  const handleConfirmImport = useCallback(async () => {
    if (!importResult?.data || importResult.data.length === 0) {
      message.warning(t('noTasksToExport'));
      return;
    }

    setIsCreating(true);
    let successCount = 0;
    let failCount = 0;

    for (const task of importResult.data) {
      try {
        const payload: CreateTaskPayload = {
          name: task.name,
          description: task.description,
          priority: task.priority,
          annotation_type: task.annotation_type,
          due_date: task.due_date,
          tags: task.tags,
        };
        await createTask.mutateAsync(payload);
        successCount++;
      } catch (error) {
        failCount++;
        console.error('Failed to create task:', error);
      }
    }

    setIsCreating(false);

    if (failCount === 0) {
      message.success(t('import.importSuccess', { count: successCount }));
      setImportResult(null);
      onSuccess();
    } else if (successCount > 0) {
      message.warning(t('batchCreatePartial', { success: successCount, fail: failCount }));
      setImportResult(null);
      onSuccess();
    } else {
      message.error(t('import.importFailed'));
    }
  }, [importResult, createTask, t, message, onSuccess]);

  // Reset state when modal closes
  const handleCancel = useCallback(() => {
    setImportResult(null);
    setIsImporting(false);
    setIsCreating(false);
    onCancel();
  }, [onCancel]);

  // Table columns for preview
  const columns = [
    {
      title: t('taskName'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: t('columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => {
        const colorMap: Record<string, string> = {
          low: 'green',
          medium: 'blue',
          high: 'orange',
          urgent: 'red',
        };
        return <Tag color={colorMap[priority] || 'default'}>{t(`priority${priority.charAt(0).toUpperCase() + priority.slice(1)}`)}</Tag>;
      },
    },
    {
      title: t('annotationType'),
      dataIndex: 'annotation_type',
      key: 'annotation_type',
      width: 150,
      render: (type: string) => {
        const typeKeyMap: Record<string, string> = {
          text_classification: 'typeTextClassification',
          ner: 'typeNER',
          sentiment: 'typeSentiment',
          qa: 'typeQA',
          custom: 'typeCustom',
        };
        return <Tag color="blue">{t(typeKeyMap[type] || 'typeCustom')}</Tag>;
      },
    },
    {
      title: t('dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '-',
    },
  ];

  return (
    <Modal
      title={t('import.title')}
      open={open}
      onCancel={handleCancel}
      width={800}
      footer={
        importResult?.data && importResult.data.length > 0 ? [
          <Button key="cancel" onClick={handleCancel}>
            {t('cancel')}
          </Button>,
          <Button
            key="confirm"
            type="primary"
            loading={isCreating}
            onClick={handleConfirmImport}
            icon={<CheckCircleOutlined />}
          >
            {t('confirm')} ({importResult.data.length} {t('export.tasks')})
          </Button>,
        ] : [
          <Button key="cancel" onClick={handleCancel}>
            {t('cancel')}
          </Button>,
        ]
      }
    >
      {!importResult ? (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Download template section */}
          <Alert
            message={t('import.downloadTemplate')}
            description={
              <Space>
                <Button 
                  icon={<DownloadOutlined />} 
                  onClick={handleDownloadTemplate}
                  size="small"
                >
                  CSV {t('import.downloadTemplate')}
                </Button>
              </Space>
            }
            type="info"
            showIcon
          />
          
          {/* Upload section */}
          <Dragger
            accept=".csv,.json,.xlsx,.xls"
            beforeUpload={handleFileImport}
            showUploadList={false}
            disabled={isImporting}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">
              {t('uploadText')}
            </p>
            <p className="ant-upload-hint">
              {t('uploadHint')}
            </p>
          </Dragger>
        </Space>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Import result summary */}
          {importResult.errors.length > 0 && (
            <Alert
              message={t('import.importFailed')}
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {importResult.errors.slice(0, 5).map((error, index) => (
                    <li key={index}>{error.message} (Row {error.row})</li>
                  ))}
                  {importResult.errors.length > 5 && (
                    <li>... {importResult.errors.length - 5} more errors</li>
                  )}
                </ul>
              }
              type="warning"
              showIcon
              icon={<WarningOutlined />}
            />
          )}
          
          {importResult.data.length > 0 && (
            <>
              <Alert
                message={t('import.importSuccess', { count: importResult.data.length })}
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
              />
              
              <Divider>{t('import.title')} - {t('list.title')}</Divider>
              
              {/* Preview table */}
              <Table
                columns={columns}
                dataSource={importResult.data.map((item, index) => ({ ...item, key: index }))}
                size="small"
                pagination={{ pageSize: 5 }}
                scroll={{ y: 300 }}
              />
            </>
          )}
        </Space>
      )}
    </Modal>
  );
};

export default TaskImportModal;
