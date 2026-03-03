/**
 * Data Structuring — File Upload Page
 *
 * Drag-and-drop file upload with format validation, size limit (100MB),
 * and upload progress display. On success, navigates to the preview page.
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Upload,
  Typography,
  Space,
  Alert,
  Button,
  message,
  Progress,
  Tag,
  Result,
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  Html5Outlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useStructuringStore } from '@/stores/structuringStore';

const { Title, Paragraph, Text } = Typography;
const { Dragger } = Upload;

// ============================================================================
// Constants
// ============================================================================

const MAX_FILE_SIZE_MB = 100;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

const ACCEPTED_EXTENSIONS = ['.pdf', '.csv', '.xlsx', '.xls', '.docx', '.html', '.htm', '.txt', '.md'];


interface FormatInfo {
  label: string;
  icon: React.ReactNode;
  color: string;
}

const FILE_FORMAT_MAP: Record<string, FormatInfo> = {
  pdf:  { label: 'PDF',   icon: <FilePdfOutlined />,  color: 'red' },
  csv:  { label: 'CSV',   icon: <FileTextOutlined />, color: 'green' },
  xlsx: { label: 'Excel', icon: <FileExcelOutlined />, color: 'blue' },
  xls:  { label: 'Excel', icon: <FileExcelOutlined />, color: 'blue' },
  docx: { label: 'Word',  icon: <FileWordOutlined />, color: 'geekblue' },
  html: { label: 'HTML',  icon: <Html5Outlined />,    color: 'orange' },
  htm:  { label: 'HTML',  icon: <Html5Outlined />,    color: 'orange' },
  txt:  { label: 'TXT',   icon: <FileTextOutlined />, color: 'default' },
  md:   { label: 'Markdown', icon: <FileTextOutlined />, color: 'purple' },
};

// ============================================================================
// Helpers
// ============================================================================

function getFileExtension(fileName: string): string {
  const dotIndex = fileName.lastIndexOf('.');
  if (dotIndex < 0) return '';
  return fileName.slice(dotIndex + 1).toLowerCase();
}

function isAcceptedFormat(fileName: string): boolean {
  const ext = getFileExtension(fileName);
  return Object.keys(FILE_FORMAT_MAP).includes(ext);
}

function isWithinSizeLimit(fileSize: number): boolean {
  return fileSize <= MAX_FILE_SIZE_BYTES;
}

// ============================================================================
// Component
// ============================================================================

const UploadPage: React.FC = () => {
  const { t } = useTranslation(['structuring', 'common']);
  const navigate = useNavigate();

  const { uploadFile, isUploading, error, clearError } = useStructuringStore();

  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadedJobId, setUploadedJobId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Reset to initial state for a new upload
  const handleReset = useCallback(() => {
    setUploadedJobId(null);
    setUploadProgress(0);
    setValidationError(null);
    clearError();
  }, [clearError]);

  // Validate file before upload
  const validateFile = useCallback((file: File): string | null => {
    if (!isAcceptedFormat(file.name)) {
      const ext = getFileExtension(file.name) || t('structuring:upload.unknownFormat', '未知');
      return t('structuring:upload.unsupportedFormat', {
        format: ext,
        supported: ACCEPTED_EXTENSIONS.join(', '),
        defaultValue: `不支持的文件格式: .${ext}。支持的格式: ${ACCEPTED_EXTENSIONS.join(', ')}`,
      });
    }

    if (!isWithinSizeLimit(file.size)) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      return t('structuring:upload.fileTooLarge', {
        size: sizeMB,
        max: MAX_FILE_SIZE_MB,
        defaultValue: `文件大小 (${sizeMB}MB) 超过上限 ${MAX_FILE_SIZE_MB}MB`,
      });
    }

    return null;
  }, [t]);

  // Handle the upload via store action
  const handleUpload = useCallback(async (file: File) => {
    setValidationError(null);
    clearError();

    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      return false;
    }

    setUploadProgress(0);

    try {
      // Simulate progress during upload
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const jobId = await uploadFile(file);

      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadedJobId(jobId);
      message.success(
        t('structuring:upload.success', { defaultValue: '文件上传成功！' }),
      );
    } catch {
      setUploadProgress(0);
      message.error(
        t('structuring:upload.failed', { defaultValue: '文件上传失败，请重试' }),
      );
    }

    // Prevent antd default upload behaviour
    return false;
  }, [uploadFile, validateFile, clearError, t]);

  const handleGoToPreview = useCallback(() => {
    if (uploadedJobId) {
      navigate(`/data-structuring/preview/${uploadedJobId}`);
    }
  }, [uploadedJobId, navigate]);

  // ---- Success state ----
  if (uploadedJobId) {
    return (
      <div style={{ padding: 24 }}>
        <Card>
          <Result
            status="success"
            icon={<CheckCircleOutlined />}
            title={t('structuring:upload.successTitle', { defaultValue: '文件上传成功' })}
            subTitle={t('structuring:upload.successSubtitle', {
              defaultValue: '系统正在处理您的文件，您可以查看处理进度。',
            })}
            extra={[
              <Button
                key="preview"
                type="primary"
                onClick={handleGoToPreview}
              >
                {t('structuring:upload.goToPreview', { defaultValue: '查看处理进度' })}
              </Button>,
              <Button key="another" onClick={handleReset}>
                {t('structuring:upload.uploadAnother', { defaultValue: '继续上传' })}
              </Button>,
            ]}
          />
        </Card>
      </div>
    );
  }

  // ---- Upload state ----
  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={2}>
            <CloudUploadOutlined style={{ marginRight: 8 }} />
            {t('structuring:upload.title', { defaultValue: '上传文件' })}
          </Title>
          <Paragraph type="secondary">
            {t('structuring:upload.description', {
              defaultValue: '上传非结构化文件，系统将通过 AI 自动分析并提取结构化数据。',
            })}
          </Paragraph>
        </div>

        {/* Validation / API error alerts */}
        {validationError && (
          <Alert
            message={t('structuring:upload.validationError', { defaultValue: '文件校验失败' })}
            description={validationError}
            type="error"
            showIcon
            closable
            onClose={() => setValidationError(null)}
          />
        )}
        {error && (
          <Alert
            message={t('structuring:upload.uploadError', { defaultValue: '上传出错' })}
            description={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
          />
        )}

        {/* Dragger upload area */}
        <Card>
          <Dragger
            accept={ACCEPTED_EXTENSIONS.join(',')}
            beforeUpload={handleUpload}
            showUploadList={false}
            disabled={isUploading}
            multiple={false}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">
              {t('structuring:upload.dragText', {
                defaultValue: '点击或拖拽文件到此区域上传',
              })}
            </p>
            <p className="ant-upload-hint">
              {t('structuring:upload.hint', {
                defaultValue: `支持 PDF、CSV、Excel、Word、HTML、TXT 格式，单文件最大 ${MAX_FILE_SIZE_MB}MB`,
              })}
            </p>
          </Dragger>

          {/* Upload progress */}
          {isUploading && (
            <div style={{ marginTop: 16 }}>
              <Progress
                percent={uploadProgress}
                status="active"
                strokeColor={{ from: '#108ee9', to: '#87d068' }}
              />
              <Text type="secondary">
                {t('structuring:upload.uploading', { defaultValue: '正在上传...' })}
              </Text>
            </div>
          )}
        </Card>

        {/* Supported formats reference */}
        <Card
          size="small"
          title={t('structuring:upload.supportedFormats', { defaultValue: '支持的文件格式' })}
        >
          <Space wrap>
            {Object.entries(FILE_FORMAT_MAP)
              .filter(([ext]) => !['xls', 'htm'].includes(ext)) // dedupe aliases
              .map(([ext, info]) => (
                <Tag key={ext} icon={info.icon} color={info.color}>
                  .{ext} ({info.label})
                </Tag>
              ))}
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default UploadPage;
