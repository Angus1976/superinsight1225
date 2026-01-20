/**
 * Workspace Management Page
 * 
 * Provides workspace management including:
 * - Hierarchy tree view
 * - Create/Edit/Delete workspaces
 * - Archive/Restore workspaces
 * - Move workspaces (drag-drop)
 * - Template creation
 */

import React, { useState } from 'react';
import { 
  Card, Tree, Button, Space, Tag, Modal, Form, Input, Select, 
  message, Row, Col, Descriptions, Dropdown, Empty, Spin
} from 'antd';
import type { TreeDataNode, TreeProps } from 'antd';
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, FolderOutlined, 
  FolderOpenOutlined, ReloadOutlined, MoreOutlined, InboxOutlined,
  UndoOutlined, DragOutlined, CopyOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { 
  workspaceApi, tenantApi,
  Workspace, WorkspaceNode, WorkspaceCreateRequest, WorkspaceUpdateRequest
} from '@/services/multiTenantApi';

const WorkspaceManagement: React.FC = () => {
  const { t } = useTranslation(['workspace', 'common']);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailVisible, setIsDetailVisible] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [selectedTenantId, setSelectedTenantId] = useState<string | undefined>();
  const [parentId, setParentId] = useState<string | undefined>();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch tenants for selector
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantApi.list({ status: 'active' }).then(res => res.data),
  });

  // Fetch workspace hierarchy
  const { data: hierarchy, isLoading, refetch } = useQuery({
    queryKey: ['workspace-hierarchy', selectedTenantId],
    queryFn: () => workspaceApi.getHierarchy(selectedTenantId).then(res => res.data),
    enabled: !!selectedTenantId,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: WorkspaceCreateRequest) => workspaceApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('createSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('createError'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkspaceUpdateRequest }) => 
      workspaceApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('updateSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('updateError'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success(t('deleteSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('deleteError'));
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success(t('archived'));
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.restore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success(t('restored'));
    },
  });

  const moveMutation = useMutation({
    mutationFn: ({ id, newParentId }: { id: string; newParentId?: string }) => 
      workspaceApi.move(id, newParentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success(t('moved'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('moveError'));
    },
  });


  // Convert hierarchy to tree data
  const convertToTreeData = (nodes: WorkspaceNode[]): TreeDataNode[] => {
    return nodes.map(node => ({
      key: node.id,
      title: (
        <Space>
          <span>{node.name}</span>
          {node.status === 'archived' && <Tag color="default">{t('statusArchived')}</Tag>}
        </Space>
      ),
      icon: node.children?.length ? <FolderOpenOutlined /> : <FolderOutlined />,
      children: node.children ? convertToTreeData(node.children) : [],
      data: node,
    }));
  };

  const treeData = hierarchy ? convertToTreeData(hierarchy) : [];

  // Find workspace by id in hierarchy
  const findWorkspace = (nodes: WorkspaceNode[], id: string): WorkspaceNode | null => {
    for (const node of nodes) {
      if (node.id === id) return node;
      if (node.children) {
        const found = findWorkspace(node.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const handleSelect: TreeProps['onSelect'] = (selectedKeys) => {
    if (selectedKeys.length > 0 && hierarchy) {
      const workspace = findWorkspace(hierarchy, selectedKeys[0] as string);
      setSelectedWorkspace(workspace);
    } else {
      setSelectedWorkspace(null);
    }
  };

  const handleDrop: TreeProps['onDrop'] = (info) => {
    const dragKey = info.dragNode.key as string;
    const dropKey = info.node.key as string;
    const dropToGap = info.dropToGap;

    if (dropToGap) {
      // Move to same level as drop target
      const dropNode = findWorkspace(hierarchy || [], dropKey);
      moveMutation.mutate({ id: dragKey, newParentId: dropNode?.parent_id });
    } else {
      // Move as child of drop target
      moveMutation.mutate({ id: dragKey, newParentId: dropKey });
    }
  };

  const handleSubmit = (values: any) => {
    if (editingWorkspace) {
      updateMutation.mutate({ id: editingWorkspace.id, data: values });
    } else {
      createMutation.mutate({ ...values, parent_id: parentId });
    }
  };

  const getContextMenu = (workspace: WorkspaceNode) => ({
    items: [
      {
        key: 'add-child',
        icon: <PlusOutlined />,
        label: t('common:addChild'),
        onClick: () => {
          setParentId(workspace.id);
          setEditingWorkspace(null);
          form.resetFields();
          setIsModalVisible(true);
        },
      },
      {
        key: 'edit',
        icon: <EditOutlined />,
        label: t('common:edit'),
        onClick: () => {
          setEditingWorkspace(workspace);
          form.setFieldsValue({
            name: workspace.name,
            description: workspace.description,
          });
          setIsModalVisible(true);
        },
      },
      {
        key: 'duplicate',
        icon: <CopyOutlined />,
        label: t('common:duplicate'),
        onClick: () => {
          message.info(t('templateInDev'));
        },
      },
      { type: 'divider' as const },
      workspace.status === 'active' ? {
        key: 'archive',
        icon: <InboxOutlined />,
        label: t('common:archive'),
        onClick: () => {
          Modal.confirm({
            title: t('confirmArchive'),
            content: t('confirmArchiveContent', { name: workspace.name }),
            onOk: () => archiveMutation.mutate(workspace.id),
          });
        },
      } : {
        key: 'restore',
        icon: <UndoOutlined />,
        label: t('common:restore'),
        onClick: () => restoreMutation.mutate(workspace.id),
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: t('common:delete'),
        danger: true,
        onClick: () => {
          Modal.confirm({
            title: t('confirmDelete'),
            content: t('confirmDeleteContent', { name: workspace.name }),
            onOk: () => deleteMutation.mutate(workspace.id),
          });
        },
      },
    ],
  });

  return (
    <div className="workspace-management">
      <Row gutter={16}>
        {/* Left: Tree View */}
        <Col span={10}>
          <Card
            title={
              <Space>
                <FolderOutlined />
                {t('hierarchy')}
              </Space>
            }
            extra={
              <Space>
                <Select
                  placeholder={t('selectTenant')}
                  style={{ width: 200 }}
                  onChange={setSelectedTenantId}
                  value={selectedTenantId}
                >
                  {tenants?.map(t => (
                    <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                  ))}
                </Select>
                <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  disabled={!selectedTenantId}
                  onClick={() => {
                    setParentId(undefined);
                    setEditingWorkspace(null);
                    form.resetFields();
                    setIsModalVisible(true);
                  }}
                >
                  {t('create')}
                </Button>
              </Space>
            }
          >
            {!selectedTenantId ? (
              <Empty description={t('selectTenantFirst')} />
            ) : isLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
            ) : treeData.length === 0 ? (
              <Empty description={t('noWorkspaces')} />
            ) : (
              <Tree
                showIcon
                draggable
                blockNode
                treeData={treeData}
                onSelect={handleSelect}
                onDrop={handleDrop}
                titleRender={(nodeData: any) => (
                  <Dropdown menu={getContextMenu(nodeData.data)} trigger={['contextMenu']}>
                    <span style={{ display: 'inline-block', width: '100%' }}>
                      {nodeData.title}
                    </span>
                  </Dropdown>
                )}
              />
            )}
            <div style={{ marginTop: 16, color: '#666', fontSize: 12 }}>
              <DragOutlined /> {t('dragHint')}
            </div>
          </Card>
        </Col>

        {/* Right: Detail Panel */}
        <Col span={14}>
          <Card title={t('details')}>
            {selectedWorkspace ? (
              <div>
                <Descriptions bordered column={2}>
                  <Descriptions.Item label={t('fields.id')}>{selectedWorkspace.id}</Descriptions.Item>
                  <Descriptions.Item label={t('fields.name')}>{selectedWorkspace.name}</Descriptions.Item>
                  <Descriptions.Item label={t('fields.status')}>
                    <Tag color={selectedWorkspace.status === 'active' ? 'success' : 'default'}>
                      {selectedWorkspace.status === 'active' ? t('status.active') : t('status.archived')}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('fields.parent')}>
                    {selectedWorkspace.parent_id || t('status.root')}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('fields.createdAt')} span={2}>
                    {new Date(selectedWorkspace.created_at).toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('fields.description')} span={2}>
                    {selectedWorkspace.description || '-'}
                  </Descriptions.Item>
                </Descriptions>
                <div style={{ marginTop: 16 }}>
                  <Space>
                    <Button
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditingWorkspace(selectedWorkspace);
                        form.setFieldsValue({
                          name: selectedWorkspace.name,
                          description: selectedWorkspace.description,
                        });
                        setIsModalVisible(true);
                      }}
                    >
                      {t('common:edit')}
                    </Button>
                    {selectedWorkspace.status === 'active' ? (
                      <Button
                        icon={<InboxOutlined />}
                        onClick={() => archiveMutation.mutate(selectedWorkspace.id)}
                      >
                        {t('common:archive')}
                      </Button>
                    ) : (
                      <Button
                        icon={<UndoOutlined />}
                        onClick={() => restoreMutation.mutate(selectedWorkspace.id)}
                      >
                        {t('common:restore')}
                      </Button>
                    )}
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => {
                        Modal.confirm({
                          title: t('confirmDelete'),
                          content: t('confirmDeleteContent', { name: selectedWorkspace.name }),
                          onOk: () => deleteMutation.mutate(selectedWorkspace.id),
                        });
                      }}
                    >
                      {t('actions.delete')}
                    </Button>
                  </Space>
                </div>
              </div>
            ) : (
              <Empty description={t('selectWorkspace')} />
            )}
          </Card>
        </Col>
      </Row>

      {/* Create/Edit Modal */}
      <Modal
        title={editingWorkspace ? t('editWorkspace') : t('createWorkspace')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label={t('form.name')}
            rules={[{ required: true, message: t('form.nameRequired') }]}
          >
            <Input placeholder={t('form.namePlaceholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('form.description')}>
            <Input.TextArea rows={3} placeholder={t('form.descriptionPlaceholder')} />
          </Form.Item>
          {parentId && (
            <Form.Item label={t('form.parentWorkspace')}>
              <Input value={parentId} disabled />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default WorkspaceManagement;
