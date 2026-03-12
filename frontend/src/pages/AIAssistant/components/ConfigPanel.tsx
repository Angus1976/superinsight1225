import React from 'react';
import { Button, Space, Card } from 'antd';
import { DatabaseOutlined, LockOutlined, SettingOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface ConfigPanelProps {
  userRole: string;
  onOpenDataSourceConfig: () => void;
  onOpenPermissionTable: () => void;
  onOpenOutputMode: () => void;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({
  userRole,
  onOpenDataSourceConfig,
  onOpenPermissionTable,
  onOpenOutputMode,
}) => {
  const { t } = useTranslation('aiAssistant');
  const isAdmin = userRole === 'admin';

  return (
    <Card size="small" title={t('configPanel.title')} style={{ marginTop: 'auto' }}>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {isAdmin && (
          <>
            <Button
              block
              icon={<DatabaseOutlined />}
              onClick={onOpenDataSourceConfig}
            >
              {t('configPanel.configDataSource')}
            </Button>
            <Button
              block
              icon={<LockOutlined />}
              onClick={onOpenPermissionTable}
            >
              {t('configPanel.configPermissions')}
            </Button>
          </>
        )}
        <Button
          block
          icon={<SettingOutlined />}
          onClick={onOpenOutputMode}
        >
          {t('configPanel.outputMode')}
        </Button>
      </Space>
    </Card>
  );
};

export default ConfigPanel;
