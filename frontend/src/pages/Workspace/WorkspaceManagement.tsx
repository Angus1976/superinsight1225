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
import { 
  workspaceApi, tenantApi,
  Workspace, WorkspaceNode, WorkspaceCreateRequest, WorkspaceUpdateRequest
} from '@/services/multiTenantApi';

const WorkspaceManagement: React.FC = () => {
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
      message.success('工作空间创建成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '工作空间创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkspaceUpdateRequest }) => 
      workspaceApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('工作空间更新成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '工作空间更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success('工作空间删除成功');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '工作空间删除失败');
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success('工作空间已归档');
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => workspaceApi.restore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success('工作空间已恢复');
    },
  });

  const moveMutation = useMutation({
    mutationFn: ({ id, newParentId }: { id: string; newParentId?: string }) => 
      workspaceApi.move(id, newParentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-hierarchy'] });
      message.success('工作空间已移动');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '移动失败');
    },
  });


  // Convert hierarchy to tree data
  const convertToTreeData = (nodes: WorkspaceNode[]): TreeDataNode[] => {
    return nodes.map(node => ({
      key: node.id,
      title: (
        <Space>
          <span>{node.name}</span>
          {node.status === 'archived' && <Tag color="default">已归档</Tag>}
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
        label: '添加子工作空间',
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
        label: '编辑',
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
        label: '复制为模板',
        onClick: () => {
          message.info('模板功能开发中');
        },
      },
      { type: 'divider' as const },
      workspace.status === 'active' ? {
        key: 'archive',
        icon: <InboxOutlined />,
        label: '归档',
        onClick: () => {
          Modal.confirm({
            title: '确认归档',
            content: `确定要归档工作空间 "${workspace.name}" 吗？`,
            onOk: () => archiveMutation.mutate(workspace.id),
          });
        },
      } : {
        key: 'restore',
        icon: <UndoOutlined />,
        label: '恢复',
        onClick: () => restoreMutation.mutate(workspace.id),
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '删除',
        danger: true,
        onClick: () => {
          Modal.confirm({
            title: '确认删除',
            content: `确定要删除工作空间 "${workspace.name}" 吗？此操作不可恢复！`,
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
                工作空间层级
              </Space>
            }
            extra={
              <Space>
                <Select
                  placeholder="选择租户"
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
                  新建
                </Button>
              </Space>
            }
          >
            {!selectedTenantId ? (
              <Empty description="请先选择租户" />
            ) : isLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
            ) : treeData.length === 0 ? (
              <Empty description="暂无工作空间" />
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
              <DragOutlined /> 拖拽可调整层级结构，右键查看更多操作
            </div>
          </Card>
        </Col>

        {/* Right: Detail Panel */}
        <Col span={14}>
          <Card title="工作空间详情">
            {selectedWorkspace ? (
              <div>
                <Descriptions bordered column={2}>
                  <Descriptions.Item label="ID">{selectedWorkspace.id}</Descriptions.Item>
                  <Descriptions.Item label="名称">{selectedWorkspace.name}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={selectedWorkspace.status === 'active' ? 'success' : 'default'}>
                      {selectedWorkspace.status === 'active' ? '活跃' : '已归档'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="父级">
                    {selectedWorkspace.parent_id || '根级'}
                  </Descriptions.Item>
                  <Descriptions.Item label="创建时间" span={2}>
                    {new Date(selectedWorkspace.created_at).toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>
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
                      编辑
                    </Button>
                    {selectedWorkspace.status === 'active' ? (
                      <Button
                        icon={<InboxOutlined />}
                        onClick={() => archiveMutation.mutate(selectedWorkspace.id)}
                      >
                        归档
                      </Button>
                    ) : (
                      <Button
                        icon={<UndoOutlined />}
                        onClick={() => restoreMutation.mutate(selectedWorkspace.id)}
                      >
                        恢复
                      </Button>
                    )}
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => {
                        Modal.confirm({
                          title: '确认删除',
                          content: `确定要删除工作空间 "${selectedWorkspace.name}" 吗？`,
                          onOk: () => deleteMutation.mutate(selectedWorkspace.id),
                        });
                      }}
                    >
                      删除
                    </Button>
                  </Space>
                </div>
              </div>
            ) : (
              <Empty description="请在左侧选择工作空间" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Create/Edit Modal */}
      <Modal
        title={editingWorkspace ? '编辑工作空间' : '新建工作空间'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="工作空间名称"
            rules={[{ required: true, message: '请输入工作空间名称' }]}
          >
            <Input placeholder="请输入工作空间名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          {parentId && (
            <Form.Item label="父级工作空间">
              <Input value={parentId} disabled />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default WorkspaceManagement;
