import React, { useEffect, useState } from 'react';
import { Modal, Table, Checkbox, Button, Spin, Empty, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { getDataSourceConfig, getRolePermissions, updateRolePermissions } from '@/services/aiAssistantApi';
import type { RolePermissionItem } from '@/services/aiAssistantApi';
import type { AIDataSource } from '@/types/aiAssistant';

interface PermissionTableModalProps {
  open: boolean;
  onClose: () => void;
}

const ROLES = ['admin', 'business_expert', 'annotator', 'viewer'];

const PermissionTableModal: React.FC<PermissionTableModalProps> = ({ open, onClose }) => {
  const { t } = useTranslation('aiAssistant');
  const [enabledSources, setEnabledSources] = useState<AIDataSource[]>([]);
  const [permMap, setPermMap] = useState<Record<string, Record<string, boolean>>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    Promise.all([getDataSourceConfig(), getRolePermissions()])
      .then(([sources, { permissions }]) => {
        const enabled = sources.filter((s) => s.enabled);
        setEnabledSources(enabled);

        // Build permission map: { role: { source_id: boolean } }
        const map: Record<string, Record<string, boolean>> = {};
        for (const role of ROLES) {
          map[role] = {};
          for (const src of enabled) {
            map[role][src.id] = false;
          }
        }
        for (const p of permissions) {
          if (map[p.role]) {
            map[p.role][p.source_id] = p.allowed;
          }
        }
        setPermMap(map);
      })
      .catch(() => message.error(t('dataSourceLoadFailed')))
      .finally(() => setLoading(false));
  }, [open, t]);

  const handleCheck = (role: string, sourceId: string, checked: boolean) => {
    setPermMap((prev) => ({
      ...prev,
      [role]: { ...prev[role], [sourceId]: checked },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const permissions: RolePermissionItem[] = [];
      for (const role of ROLES) {
        for (const src of enabledSources) {
          permissions.push({ role, source_id: src.id, allowed: !!permMap[role]?.[src.id] });
        }
      }
      await updateRolePermissions(permissions);
      message.success(t('permissionSaved'));
      onClose();
    } catch {
      message.error(t('permissionSaveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => t(`role.${role}`),
    },
    ...enabledSources.map((src) => ({
      title: t(`source.${src.id}`),
      dataIndex: src.id,
      key: src.id,
      render: (_: unknown, record: { role: string }) => (
        <Checkbox
          checked={!!permMap[record.role]?.[src.id]}
          onChange={(e) => handleCheck(record.role, src.id, e.target.checked)}
        />
      ),
    })),
  ];

  const dataSource = ROLES.map((role) => ({ key: role, role }));

  return (
    <Modal
      title={t('permissionModal.title')}
      open={open}
      onCancel={onClose}
      width={Math.max(520, enabledSources.length * 120 + 200)}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('permissionModal.cancel')}
        </Button>,
        <Button key="save" type="primary" loading={saving} onClick={handleSave}>
          {t('permissionModal.save')}
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        {enabledSources.length === 0 && !loading ? (
          <Empty description={t('permissionModal.noEnabledSources')} />
        ) : (
          <Table
            columns={columns}
            dataSource={dataSource}
            pagination={false}
            size="middle"
          />
        )}
      </Spin>
    </Modal>
  );
};

export default PermissionTableModal;
