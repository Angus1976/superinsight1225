/**
 * Collaborative Ontology Editor Component (协作本体编辑器)
 * 
 * Visual editor for ontology elements with real-time collaboration features.
 * Shows presence indicators, element locking UI, and WebSocket integration.
 * 
 * Requirements: Task 22.1 - Collaborative Editing
 * Validates: Requirements 7.1, 7.4
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Tree,
  Typography,
  Space,
  Button,
  Avatar,
  Tooltip,
  Badge,
  Tag,
  Alert,
  Spin,
  Empty,
  Divider,
  message,
  Popconfirm,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import {
  NodeIndexOutlined,
  BranchesOutlined,
  LockOutlined,
  UnlockOutlined,
  UserOutlined,
  TeamOutlined,
  SyncOutlined,
  DisconnectOutlined,
  EditOutlined,
  EyeOutlined,
  SaveOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ontologyCollaborationApi,
  CollaborationSession,
  ElementLock,
  OntologyTemplate,
  EntityTypeDefinition,
  RelationTypeDefinition,
} from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;

// Presence status colors
const PRESENCE_COLORS = [
  '#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1',
  '#13c2c2', '#eb2f96', '#fa8c16', '#a0d911', '#2f54eb',
];

interface Participant {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  isOnline: boolean;
  currentElement?: string;
}

interface CollaborativeOntologyEditorProps {
  ontologyId: string;
  currentUserId: string;
  currentUserName: string;
  template?: OntologyTemplate;
  onSave?: (changes: Record<string, unknown>) => void;
}

const CollaborativeOntologyEditor: React.FC<CollaborativeOntologyEditorProps> = ({
  ontologyId,
  currentUserId,
  currentUserName,
  template,
  onSave,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  
  // State
  const [session, setSession] = useState<CollaborationSession | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [lockedElements, setLockedElements] = useState<Record<string, ElementLock>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<Record<string, unknown>>({});

  // Create or join session
  const createSessionMutation = useMutation({
    mutationFn: () => ontologyCollaborationApi.createSession(ontologyId),
    onSuccess: (newSession) => {
      setSession(newSession);
      connectWebSocket(newSession.id);
    },
    onError: () => {
      message.error(t('ontology:collaboration.createSessionFailed'));
    },
  });

  // Lock element mutation
  const lockElementMutation = useMutation({
    mutationFn: ({ sessionId, elementId }: { sessionId: string; elementId: string }) =>
      ontologyCollaborationApi.lockElement(sessionId, elementId, currentUserId),
    onSuccess: (lock) => {
      setLockedElements((prev) => ({ ...prev, [lock.element_id]: lock }));
      message.success(t('ontology:collaboration.elementLocked'));
    },
    onError: () => {
      message.error(t('ontology:collaboration.lockFailed'));
    },
  });

  // Unlock element mutation
  const unlockElementMutation = useMutation({
    mutationFn: ({ sessionId, elementId }: { sessionId: string; elementId: string }) =>
      ontologyCollaborationApi.unlockElement(sessionId, elementId),
    onSuccess: (_, { elementId }) => {
      setLockedElements((prev) => {
        const newLocks = { ...prev };
        delete newLocks[elementId];
        return newLocks;
      });
      message.success(t('ontology:collaboration.elementUnlocked'));
    },
    onError: () => {
      message.error(t('ontology:collaboration.unlockFailed'));
    },
  });

  // Connect to WebSocket
  const connectWebSocket = useCallback((sessionId: string) => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/collaboration/sessions/${sessionId}/ws`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsConnected(true);
      // Send join message
      ws.send(JSON.stringify({
        type: 'join',
        user_id: currentUserId,
        user_name: currentUserName,
      }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      // Attempt reconnection after 3 seconds
      setTimeout(() => {
        if (session) {
          connectWebSocket(session.id);
        }
      }, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
    
    wsRef.current = ws;
  }, [currentUserId, currentUserName, session]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data: Record<string, unknown>) => {
    switch (data.type) {
      case 'participant_joined':
        setParticipants((prev) => {
          const exists = prev.some((p) => p.id === data.user_id);
          if (exists) return prev;
          return [
            ...prev,
            {
              id: data.user_id as string,
              name: data.user_name as string,
              color: PRESENCE_COLORS[prev.length % PRESENCE_COLORS.length],
              isOnline: true,
            },
          ];
        });
        break;
        
      case 'participant_left':
        setParticipants((prev) =>
          prev.map((p) =>
            p.id === data.user_id ? { ...p, isOnline: false } : p
          )
        );
        break;
        
      case 'element_locked':
        setLockedElements((prev) => ({
          ...prev,
          [data.element_id as string]: data.lock as ElementLock,
        }));
        break;
        
      case 'element_unlocked':
        setLockedElements((prev) => {
          const newLocks = { ...prev };
          delete newLocks[data.element_id as string];
          return newLocks;
        });
        break;
        
      case 'element_changed':
        // Handle element change from another user
        queryClient.invalidateQueries({ queryKey: ['ontology', ontologyId] });
        break;
        
      case 'cursor_moved':
        setParticipants((prev) =>
          prev.map((p) =>
            p.id === data.user_id
              ? { ...p, currentElement: data.element_id as string }
              : p
          )
        );
        break;
        
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  }, [ontologyId, queryClient]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Start session on mount
  useEffect(() => {
    createSessionMutation.mutate();
  }, []);

  // Handle element selection
  const handleSelectElement = (elementId: string) => {
    setSelectedElement(elementId);
    
    // Send cursor position to other participants
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({
        type: 'cursor_move',
        element_id: elementId,
      }));
    }
  };

  // Handle lock element
  const handleLockElement = () => {
    if (!session || !selectedElement) return;
    lockElementMutation.mutate({
      sessionId: session.id,
      elementId: selectedElement,
    });
  };

  // Handle unlock element
  const handleUnlockElement = () => {
    if (!session || !selectedElement) return;
    unlockElementMutation.mutate({
      sessionId: session.id,
      elementId: selectedElement,
    });
  };

  // Check if element is locked by current user
  const isLockedByMe = (elementId: string): boolean => {
    const lock = lockedElements[elementId];
    return lock?.locked_by === currentUserId;
  };

  // Check if element is locked by another user
  const isLockedByOther = (elementId: string): boolean => {
    const lock = lockedElements[elementId];
    return lock && lock.locked_by !== currentUserId;
  };

  // Get lock info for element
  const getLockInfo = (elementId: string): ElementLock | undefined => {
    return lockedElements[elementId];
  };

  // Build tree data from template
  const buildTreeData = (): DataNode[] => {
    if (!template) return [];

    const entityNodes: DataNode[] = template.entity_types.map((et) => ({
      key: `entity-${et.id}`,
      title: (
        <Space>
          <NodeIndexOutlined />
          <Text>{et.name}</Text>
          {isLockedByMe(`entity-${et.id}`) && (
            <Tag color="blue" icon={<LockOutlined />}>
              {t('ontology:collaboration.lockedByYou')}
            </Tag>
          )}
          {isLockedByOther(`entity-${et.id}`) && (
            <Tag color="red" icon={<LockOutlined />}>
              {t('ontology:collaboration.lockedByOther')}
            </Tag>
          )}
          {participants
            .filter((p) => p.currentElement === `entity-${et.id}` && p.id !== currentUserId)
            .map((p) => (
              <Tooltip key={p.id} title={p.name}>
                <Avatar
                  size="small"
                  style={{ backgroundColor: p.color }}
                >
                  {p.name.charAt(0)}
                </Avatar>
              </Tooltip>
            ))}
        </Space>
      ),
      children: et.attributes?.map((attr) => ({
        key: `entity-${et.id}-attr-${attr.name}`,
        title: (
          <Space>
            <Text type="secondary">{attr.name}</Text>
            <Tag>{attr.type}</Tag>
            {attr.required && <Tag color="red">{t('common:required')}</Tag>}
          </Space>
        ),
        isLeaf: true,
      })),
    }));

    const relationNodes: DataNode[] = template.relation_types.map((rt) => ({
      key: `relation-${rt.id}`,
      title: (
        <Space>
          <BranchesOutlined />
          <Text>{rt.name}</Text>
          <Text type="secondary">({rt.source_type} → {rt.target_type})</Text>
          {isLockedByMe(`relation-${rt.id}`) && (
            <Tag color="blue" icon={<LockOutlined />}>
              {t('ontology:collaboration.lockedByYou')}
            </Tag>
          )}
          {isLockedByOther(`relation-${rt.id}`) && (
            <Tag color="red" icon={<LockOutlined />}>
              {t('ontology:collaboration.lockedByOther')}
            </Tag>
          )}
        </Space>
      ),
      isLeaf: true,
    }));

    return [
      {
        key: 'entities',
        title: (
          <Space>
            <NodeIndexOutlined />
            <Text strong>{t('ontology:template.entityTypes')}</Text>
            <Badge count={entityNodes.length} style={{ backgroundColor: '#52c41a' }} />
          </Space>
        ),
        children: entityNodes,
      },
      {
        key: 'relations',
        title: (
          <Space>
            <BranchesOutlined />
            <Text strong>{t('ontology:template.relationTypes')}</Text>
            <Badge count={relationNodes.length} style={{ backgroundColor: '#1890ff' }} />
          </Space>
        ),
        children: relationNodes,
      },
    ];
  };

  // Render participants panel
  const renderParticipantsPanel = () => (
    <Card
      size="small"
      title={
        <Space>
          <TeamOutlined />
          {t('ontology:collaboration.participants')}
          <Badge count={participants.filter((p) => p.isOnline).length} />
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Space wrap>
        {participants.map((participant) => (
          <Tooltip
            key={participant.id}
            title={
              <div>
                <div>{participant.name}</div>
                <div>
                  {participant.isOnline
                    ? t('ontology:collaboration.online')
                    : t('ontology:collaboration.offline')}
                </div>
                {participant.currentElement && (
                  <div>
                    {t('ontology:collaboration.viewing')}: {participant.currentElement}
                  </div>
                )}
              </div>
            }
          >
            <Badge
              dot
              status={participant.isOnline ? 'success' : 'default'}
              offset={[-4, 4]}
            >
              <Avatar
                style={{ backgroundColor: participant.color }}
                icon={<UserOutlined />}
              >
                {participant.name.charAt(0)}
              </Avatar>
            </Badge>
          </Tooltip>
        ))}
        {participants.length === 0 && (
          <Text type="secondary">{t('ontology:collaboration.noParticipants')}</Text>
        )}
      </Space>
    </Card>
  );

  // Render connection status
  const renderConnectionStatus = () => (
    <Alert
      message={
        <Space>
          {isConnected ? (
            <>
              <SyncOutlined spin style={{ color: '#52c41a' }} />
              {t('ontology:collaboration.connected')}
            </>
          ) : (
            <>
              <DisconnectOutlined style={{ color: '#f5222d' }} />
              {t('ontology:collaboration.disconnected')}
            </>
          )}
        </Space>
      }
      type={isConnected ? 'success' : 'error'}
      showIcon={false}
      style={{ marginBottom: 16 }}
    />
  );

  // Render element actions
  const renderElementActions = () => {
    if (!selectedElement) return null;

    const isLocked = isLockedByMe(selectedElement);
    const isLockedOther = isLockedByOther(selectedElement);
    const lockInfo = getLockInfo(selectedElement);

    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>{t('ontology:collaboration.selectedElement')}</Text>
          <Text code>{selectedElement}</Text>
          
          <Divider style={{ margin: '8px 0' }} />
          
          <Space>
            {!isLocked && !isLockedOther && (
              <Button
                type="primary"
                icon={<LockOutlined />}
                onClick={handleLockElement}
                loading={lockElementMutation.isPending}
              >
                {t('ontology:collaboration.lockElement')}
              </Button>
            )}
            
            {isLocked && (
              <Button
                icon={<UnlockOutlined />}
                onClick={handleUnlockElement}
                loading={unlockElementMutation.isPending}
              >
                {t('ontology:collaboration.unlockElement')}
              </Button>
            )}
            
            {isLockedOther && lockInfo && (
              <Alert
                message={t('ontology:collaboration.lockedByUser', {
                  user: lockInfo.locked_by,
                })}
                type="warning"
                showIcon
              />
            )}
            
            {isLocked && (
              <Button
                type="primary"
                icon={<EditOutlined />}
              >
                {t('ontology:collaboration.editElement')}
              </Button>
            )}
          </Space>
        </Space>
      </Card>
    );
  };

  if (createSessionMutation.isPending) {
    return (
      <Card>
        <Spin tip={t('ontology:collaboration.creatingSession')}>
          <div style={{ height: 200 }} />
        </Spin>
      </Card>
    );
  }

  return (
    <div className="collaborative-ontology-editor">
      {renderConnectionStatus()}
      
      <Row gutter={16}>
        <Col span={6}>
          {renderParticipantsPanel()}
          {renderElementActions()}
        </Col>
        
        <Col span={18}>
          <Card
            title={
              <Space>
                <NodeIndexOutlined />
                {t('ontology:collaboration.ontologyStructure')}
              </Space>
            }
            extra={
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['ontology', ontologyId] })}
                >
                  {t('common:refresh')}
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={() => onSave?.(pendingChanges)}
                  disabled={Object.keys(pendingChanges).length === 0}
                >
                  {t('common:save')}
                </Button>
              </Space>
            }
          >
            {template ? (
              <Tree
                showLine
                defaultExpandAll
                treeData={buildTreeData()}
                onSelect={(selectedKeys) => {
                  if (selectedKeys.length > 0) {
                    handleSelectElement(selectedKeys[0] as string);
                  }
                }}
                selectedKeys={selectedElement ? [selectedElement] : []}
              />
            ) : (
              <Empty description={t('ontology:collaboration.noOntology')} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CollaborativeOntologyEditor;
