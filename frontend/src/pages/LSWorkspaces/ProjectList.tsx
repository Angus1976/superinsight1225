/**
 * Label Studio Workspace Project List Component
 *
 * Displays and manages projects associated with a workspace:
 * - Project list
 * - Associate/Remove projects
 * - Project metadata display
 */

import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Empty,
  Typography,
  Tooltip,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  DeleteOutlined,
  FolderOutlined,
  LinkOutlined,
  ExclamationCircleOutlined,
  ExternalLinkOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useLSWorkspaceProjects,
  useAssociateLSProject,
  useRemoveLSProjectAssociation,
  useLSWorkspacePermissions,
} from '@/hooks/useLSWorkspaces';
import type { LSWorkspaceProject } from '@/types/ls-workspace';

const { Text } = Typography;

interface Props {
  workspaceId: string;
}

const LSWorkspaceProjectList: React.FC<Props> = ({ workspaceId }) => {
  const { t } = useTranslation(['lsWorkspace', 'common']);
  const [isAssociateModalVisible, setIsAssociateModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Fetch projects and permissions
  const { data: projectsData, isLoading } = useLSWorkspaceProjects(workspaceId);
  const { data: myPermissions } = useLSWorkspacePermissions(workspaceId);

  // Mutations
  const associateMutation = useAssociateLSProject();
  const removeMutation = useRemoveLSProjectAssociation();

  const projects = projectsData?.items ?? [];
  const canManageProjects =
    myPermissions?.permissions.includes('project:create') ||
    myPermissions?.permissions.includes('project:delete') ||
    false;

  const handleAssociateProject = () => {
    form.resetFields();
    setIsAssociateModalVisible(true);
  };

  const handleRemoveAssociation = (project: LSWorkspaceProject) => {
    Modal.confirm({
      title: t('project.confirmRemove', { defaultValue: 'Remove Project Association' }),
      icon: <ExclamationCircleOutlined />,
      content: t('project.confirmRemoveContent', {
        name: project.project_title || project.label_studio_project_id,
        defaultValue: `Are you sure you want to remove project "${project.project_title || project.label_studio_project_id}" from this workspace?`,
      }),
      okText: t('common:remove', { defaultValue: 'Remove' }),
      okType: 'danger',
      cancelText: t('common:cancel', { defaultValue: 'Cancel' }),
      onOk: async () => {
        try {
          await removeMutation.mutateAsync({
            workspaceId,
            projectId: project.label_studio_project_id,
          });
        } catch (error) {
          // Error handled by hook
        }
      },
    });
  };

  const handleSubmit = async (values: { label_studio_project_id: string }) => {
    try {
      await associateMutation.mutateAsync({
        workspaceId,
        request: {
          label_studio_project_id: values.label_studio_project_id,
        },
      });
      setIsAssociateModalVisible(false);
      form.resetFields();
    } catch (error) {
      // Error handled by hook
    }
  };

  const columns: ColumnsType<LSWorkspaceProject> = [
    {
      title: t('project.columns.project', { defaultValue: 'Project' }),
      key: 'project',
      render: (_, record) => (
        <Space>
          <FolderOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>
              {record.project_title || t('project.untitled', { defaultValue: 'Untitled Project' })}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ID: {record.label_studio_project_id}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: t('project.columns.description', { defaultValue: 'Description' }),
      dataIndex: 'project_description',
      key: 'description',
      ellipsis: true,
      render: (description: string) => (
        <Tooltip title={description}>
          <Text type="secondary">
            {description
              ? description.slice(0, 50) + (description.length > 50 ? '...' : '')
              : '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: t('project.columns.associatedAt', { defaultValue: 'Associated' }),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => (date ? new Date(date).toLocaleDateString() : '-'),
    },
    {
      title: t('project.columns.actions', { defaultValue: 'Actions' }),
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('project.openInLabelStudio', { defaultValue: 'Open in Label Studio' })}>
            <Button
              type="text"
              size="small"
              icon={<ExternalLinkOutlined />}
              onClick={() => {
                // Open project in Label Studio (assuming standard URL pattern)
                const labelStudioUrl = `/label-studio/projects/${record.label_studio_project_id}`;
                window.open(labelStudioUrl, '_blank');
              }}
            />
          </Tooltip>
          <Tooltip
            title={
              !canManageProjects
                ? t('project.cannotRemove', { defaultValue: 'No permission to remove' })
                : t('project.remove', { defaultValue: 'Remove' })
            }
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={!canManageProjects}
              onClick={() => handleRemoveAssociation(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="ls-workspace-project-list">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          icon={<LinkOutlined />}
          onClick={handleAssociateProject}
          disabled={!canManageProjects}
        >
          {t('project.associateProject', { defaultValue: 'Associate Project' })}
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={projects}
        loading={isLoading}
        rowKey="id"
        size="small"
        pagination={{
          pageSize: 5,
          showSizeChanger: false,
          showTotal: (total) =>
            t('project.totalProjects', {
              total,
              defaultValue: `${total} projects`,
            }),
        }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('project.noProjects', { defaultValue: 'No projects in this workspace' })}
            >
              {canManageProjects && (
                <Button type="primary" icon={<LinkOutlined />} onClick={handleAssociateProject}>
                  {t('project.associateFirstProject', { defaultValue: 'Associate a Project' })}
                </Button>
              )}
            </Empty>
          ),
        }}
      />

      {/* Associate Project Modal */}
      <Modal
        title={t('project.associateProject', { defaultValue: 'Associate Project' })}
        open={isAssociateModalVisible}
        onCancel={() => {
          setIsAssociateModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={associateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="label_studio_project_id"
            label={t('project.form.projectId', { defaultValue: 'Label Studio Project ID' })}
            rules={[
              {
                required: true,
                message: t('project.form.projectIdRequired', { defaultValue: 'Please enter project ID' }),
              },
            ]}
            help={t('project.form.projectIdHelp', {
              defaultValue: 'Enter the Label Studio project ID to associate with this workspace',
            })}
          >
            <Input
              placeholder={t('project.form.projectIdPlaceholder', { defaultValue: 'e.g., 123 or project-uuid' })}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default LSWorkspaceProjectList;
