/**
 * Collaboration Indicator Component
 *
 * Displays real-time collaboration status:
 * - Active annotators on the same project/task
 * - Conflict warnings
 * - Annotation locks
 * - Team member presence
 */

import React, { useState, useEffect } from 'react';
import {
  Badge,
  Avatar,
  Space,
  Tooltip,
  Popover,
  Card,
  Tag,
  Alert,
  Divider,
  List,
} from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  WarningOutlined,
  LockOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

import { useWebSocket } from '@/hooks/useWebSocket';

interface Collaborator {
  userId: number;
  username: string;
  avatar?: string;
  status: 'viewing' | 'editing' | 'idle';
  currentTask?: number;
  lastActivity: string;
  color: string;
}

interface ConflictWarning {
  warningId: string;
  type: 'concurrent_edit' | 'lock_conflict' | 'version_mismatch';
  message: string;
  conflictingUser?: string;
  timestamp: string;
}

interface CollaborationIndicatorProps {
  projectId: number;
  taskId?: number;
}

const CollaborationIndicator: React.FC<CollaborationIndicatorProps> = ({
  projectId,
  taskId,
}) => {
  const { t } = useTranslation(['annotation', 'common', 'collaboration']);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [conflicts, setConflicts] = useState<ConflictWarning[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket connection for real-time collaboration
  const ws = useWebSocket(
    `/api/v1/collaboration/ws?project_id=${projectId}${taskId ? `&task_id=${taskId}` : ''}`
  );

  useEffect(() => {
    if (!ws) return;

    ws.on('connect', () => {
      setWsConnected(true);
    });

    ws.on('disconnect', () => {
      setWsConnected(false);
    });

    ws.on('collaborators_update', (data: { collaborators: Collaborator[] }) => {
      setCollaborators(data.collaborators);
    });

    ws.on('user_joined', (data: Collaborator) => {
      setCollaborators((prev) => {
        const existing = prev.find((c) => c.userId === data.userId);
        if (existing) {
          return prev.map((c) => (c.userId === data.userId ? data : c));
        }
        return [...prev, data];
      });
    });

    ws.on('user_left', (data: { userId: number }) => {
      setCollaborators((prev) => prev.filter((c) => c.userId !== data.userId));
    });

    ws.on('user_status_changed', (data: { userId: number; status: Collaborator['status'] }) => {
      setCollaborators((prev) =>
        prev.map((c) => (c.userId === data.userId ? { ...c, status: data.status } : c))
      );
    });

    ws.on('conflict_warning', (data: ConflictWarning) => {
      setConflicts((prev) => [data, ...prev].slice(0, 5)); // Keep last 5 conflicts
    });

    ws.on('conflict_resolved', (data: { warningId: string }) => {
      setConflicts((prev) => prev.filter((c) => c.warningId !== data.warningId));
    });

    return () => {
      ws.off('connect');
      ws.off('disconnect');
      ws.off('collaborators_update');
      ws.off('user_joined');
      ws.off('user_left');
      ws.off('user_status_changed');
      ws.off('conflict_warning');
      ws.off('conflict_resolved');
    };
  }, [ws]);

  const getStatusIcon = (status: Collaborator['status']) => {
    switch (status) {
      case 'editing':
        return <EditOutlined style={{ color: '#52c41a' }} />;
      case 'viewing':
        return <EyeOutlined style={{ color: '#1890ff' }} />;
      default:
        return <UserOutlined style={{ color: '#999' }} />;
    }
  };

  const getStatusText = (status: Collaborator['status']) => {
    switch (status) {
      case 'editing':
        return t('collaboration:status.editing');
      case 'viewing':
        return t('collaboration:status.viewing');
      default:
        return t('collaboration:status.idle');
    }
  };

  const getConflictIcon = (type: ConflictWarning['type']) => {
    switch (type) {
      case 'lock_conflict':
        return <LockOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <WarningOutlined style={{ color: '#faad14' }} />;
    }
  };

  const activeCollaborators = collaborators.filter((c) => c.status !== 'idle');
  const hasConflicts = conflicts.length > 0;

  const collaboratorsContent = (
    <Card
      title={
        <Space>
          <TeamOutlined />
          {t('collaboration:titles.active_collaborators')}
        </Space>
      }
      size="small"
      style={{ width: 300 }}
    >
      {collaborators.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 16, color: '#999' }}>
          {t('collaboration:messages.no_collaborators')}
        </div>
      ) : (
        <>
          <List
            dataSource={collaborators}
            renderItem={(collaborator) => (
              <List.Item key={collaborator.userId}>
                <List.Item.Meta
                  avatar={
                    <Badge status={collaborator.status === 'idle' ? 'default' : 'success'} dot>
                      <Avatar
                        src={collaborator.avatar}
                        icon={<UserOutlined />}
                        style={{ backgroundColor: collaborator.color }}
                      />
                    </Badge>
                  }
                  title={collaborator.username}
                  description={
                    <Space size="small">
                      {getStatusIcon(collaborator.status)}
                      <span style={{ fontSize: 12 }}>
                        {getStatusText(collaborator.status)}
                      </span>
                      {collaborator.currentTask && taskId && collaborator.currentTask === taskId && (
                        <Tag color="blue" style={{ fontSize: 11 }}>
                          {t('collaboration:labels.same_task')}
                        </Tag>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
            size="small"
          />

          {hasConflicts && (
            <>
              <Divider style={{ margin: '12px 0' }} />
              <Alert
                message={t('collaboration:warnings.conflicts_detected')}
                description={
                  <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
                    {conflicts.map((conflict) => (
                      <div key={conflict.warningId} style={{ fontSize: 12 }}>
                        <Space>
                          {getConflictIcon(conflict.type)}
                          {conflict.message}
                        </Space>
                      </div>
                    ))}
                  </Space>
                }
                type="warning"
                showIcon
                icon={<WarningOutlined />}
              />
            </>
          )}
        </>
      )}
    </Card>
  );

  return (
    <div className="collaboration-indicator">
      <Popover
        content={collaboratorsContent}
        title={null}
        trigger="click"
        placement="bottomRight"
      >
        <Badge
          count={activeCollaborators.length}
          showZero={false}
          offset={[-5, 5]}
          status={wsConnected ? 'success' : 'default'}
        >
          <Tooltip
            title={
              wsConnected
                ? t('collaboration:tooltips.collaborators_active', {
                    count: activeCollaborators.length,
                  })
                : t('common:status.disconnected')
            }
          >
            <Space
              style={{
                cursor: 'pointer',
                padding: '4px 12px',
                borderRadius: 4,
                border: hasConflicts ? '1px solid #faad14' : '1px solid #d9d9d9',
                backgroundColor: hasConflicts ? '#fffbe6' : '#fff',
              }}
            >
              {hasConflicts && <WarningOutlined style={{ color: '#faad14' }} />}
              <TeamOutlined />
              {activeCollaborators.length > 0 && (
                <Avatar.Group
                  maxCount={3}
                  maxStyle={{ color: '#f56a00', backgroundColor: '#fde3cf' }}
                  size="small"
                >
                  {activeCollaborators.map((collaborator) => (
                    <Avatar
                      key={collaborator.userId}
                      src={collaborator.avatar}
                      icon={<UserOutlined />}
                      style={{ backgroundColor: collaborator.color }}
                    />
                  ))}
                </Avatar.Group>
              )}
            </Space>
          </Tooltip>
        </Badge>
      </Popover>
    </div>
  );
};

export default CollaborationIndicator;
