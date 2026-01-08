import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Tooltip,
  message,
  Typography,
  Popconfirm,
  Timeline,
  Descriptions,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  EyeOutlined,
  DeleteOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

export interface RuleVersion {
  id: string;
  ruleId: string;
  version: string;
  name: string;
  description?: string;
  config: Record<string, unknown>;
  createdBy: string;
  createdAt: string;
  isActive: boolean;
  changeLog?: string;
  tags?: string[];
}

interface RuleVersionManagerProps {
  ruleId: string;
  versions: RuleVersion[];
  onRollback: (versionId: string) => Promise<void>;
  onDeleteVersion: (versionId: string) => Promise<void>;
  onViewVersion: (version: RuleVersion) => void;
  loading?: boolean;
}

const RuleVersionManager: React.FC<RuleVersionManagerProps> = ({
  ruleId,
  versions,
  onRollback,
  onDeleteVersion,
  onViewVersion,
  loading = false,
}) => {
  const { t } = useTranslation();
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<RuleVersion | null>(null);

  const handleRollback = async (version: RuleVersion) => {
    try {
      await onRollback(version.id);
      message.success(t('quality.messages.ruleUpdated'));
    } catch (error) {
      message.error(t('common.operationFailed'));
    }
  };

  const handleDeleteVersion = async (versionId: string) => {
    try {
      await onDeleteVersion(versionId);
      message.success(t('quality.messages.ruleDeleted'));
    } catch (error) {
      message.error(t('common.operationFailed'));
    }
  };

  const handleViewDetail = (version: RuleVersion) => {
    setSelectedVersion(version);
    setDetailModalOpen(true);
    onViewVersion(version);
  };

  const columns: ColumnsType<RuleVersion> = [
    {
      title: t('quality.rules.version'),
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version, record) => (
        <Space>
          <Text strong>{version}</Text>
          {record.isActive && <Tag color="green">{t('common.active')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('quality.rules.name'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: t('common.tags'),
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[]) => (
        <Space wrap>
          {tags?.map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('common.createdBy'),
      dataIndex: 'createdBy',
      key: 'createdBy',
      width: 120,
    },
    {
      title: t('common.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('common.view')}>
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          
          {!record.isActive && (
            <Tooltip title={t('quality.rules.rollback')}>
              <Popconfirm
                title={t('common.confirmRollback')}
                description={`${t('quality.rules.version')}: ${record.version}`}
                onConfirm={() => handleRollback(record)}
              >
                <Button
                  type="text"
                  size="small"
                  icon={<RollbackOutlined />}
                />
              </Popconfirm>
            </Tooltip>
          )}
          
          {!record.isActive && (
            <Tooltip title={t('common.delete')}>
              <Popconfirm
                title={t('common.confirmDelete')}
                description={`${t('quality.rules.version')}: ${record.version}`}
                onConfirm={() => handleDeleteVersion(record.id)}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Popconfirm>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const renderTimeline = () => {
    const sortedVersions = [...versions].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

    return (
      <Timeline
        items={sortedVersions.map((version) => ({
          color: version.isActive ? 'green' : 'blue',
          dot: version.isActive ? <BranchesOutlined /> : <HistoryOutlined />,
          children: (
            <div>
              <Space>
                <Text strong>{version.version}</Text>
                {version.isActive && <Tag color="green">{t('common.active')}</Tag>}
              </Space>
              <div>
                <Text type="secondary">{version.name}</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {new Date(version.createdAt).toLocaleString()} - {version.createdBy}
                </Text>
              </div>
              {version.changeLog && (
                <div style={{ marginTop: 4 }}>
                  <Text style={{ fontSize: '12px' }}>{version.changeLog}</Text>
                </div>
              )}
            </div>
          ),
        }))}
      />
    );
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            {t('quality.rules.version')} {t('common.history')}
          </Space>
        }
        extra={
          <Text type="secondary">
            {t('common.total')}: {versions.length}
          </Text>
        }
      >
        <Table
          columns={columns}
          dataSource={versions}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} ${t('common.of')} ${total} ${t('common.items')}`,
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: '16px 0' }}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label={t('quality.rules.description')}>
                    {record.description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('common.changeLog')}>
                    {record.changeLog || '-'}
                  </Descriptions.Item>
                </Descriptions>
                
                <div style={{ marginTop: 16 }}>
                  <Text strong>{t('quality.rules.config')}:</Text>
                  <pre style={{ 
                    background: '#f5f5f5', 
                    padding: 8, 
                    borderRadius: 4, 
                    marginTop: 8,
                    fontSize: '12px',
                  }}>
                    {JSON.stringify(record.config, null, 2)}
                  </pre>
                </div>
              </div>
            ),
          }}
        />
      </Card>

      <Card
        title={t('common.timeline')}
        style={{ marginTop: 16 }}
      >
        {renderTimeline()}
      </Card>

      <Modal
        title={`${t('quality.rules.version')} ${selectedVersion?.version} - ${t('common.details')}`}
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedVersion(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('common.close')}
          </Button>,
          selectedVersion && !selectedVersion.isActive && (
            <Button
              key="rollback"
              type="primary"
              icon={<RollbackOutlined />}
              onClick={() => {
                handleRollback(selectedVersion);
                setDetailModalOpen(false);
              }}
            >
              {t('quality.rules.rollback')}
            </Button>
          ),
        ]}
        width={800}
      >
        {selectedVersion && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label={t('quality.rules.version')}>
                <Space>
                  {selectedVersion.version}
                  {selectedVersion.isActive && <Tag color="green">{t('common.active')}</Tag>}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label={t('quality.rules.name')}>
                {selectedVersion.name}
              </Descriptions.Item>
              <Descriptions.Item label={t('common.createdBy')}>
                {selectedVersion.createdBy}
              </Descriptions.Item>
              <Descriptions.Item label={t('common.createdAt')}>
                {new Date(selectedVersion.createdAt).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('quality.rules.description')} span={2}>
                {selectedVersion.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('common.changeLog')} span={2}>
                {selectedVersion.changeLog || '-'}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16 }}>
              <Text strong>{t('quality.rules.config')}:</Text>
              <pre style={{ 
                background: '#f5f5f5', 
                padding: 16, 
                borderRadius: 4, 
                marginTop: 8,
                maxHeight: 300,
                overflow: 'auto',
              }}>
                {JSON.stringify(selectedVersion.config, null, 2)}
              </pre>
            </div>

            {selectedVersion.tags && selectedVersion.tags.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Text strong>{t('common.tags')}:</Text>
                <div style={{ marginTop: 8 }}>
                  <Space wrap>
                    {selectedVersion.tags.map((tag) => (
                      <Tag key={tag} color="blue">
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RuleVersionManager;