import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Card, Menu, Typography, Space } from 'antd';
import {
  DatabaseOutlined,
  DashboardOutlined,
  TableOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Paragraph } = Typography;

const DatalakePage: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const location = useLocation();

  const currentKey = location.pathname.split('/').pop() || 'datalake';

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={3}>
            <DatabaseOutlined style={{ marginRight: 8 }} />
            {t('dataSync:datalake.title', '数据湖/数仓管理')}
          </Title>
          <Paragraph type="secondary">
            {t('dataSync:datalake.description', '管理数据湖和数仓连接，浏览 Schema，查看看板')}
          </Paragraph>
        </div>

        <Card style={{ marginBottom: 16 }}>
          <Menu mode="horizontal" selectedKeys={[currentKey]}>
            <Menu.Item key="sources" icon={<DatabaseOutlined />}>
              <Link to="/data-sync/datalake/sources">
                {t('dataSync:datalake.nav.sources', '数据源管理')}
              </Link>
            </Menu.Item>
            <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
              <Link to="/data-sync/datalake/dashboard">
                {t('dataSync:datalake.nav.dashboard', '可视化看板')}
              </Link>
            </Menu.Item>
            <Menu.Item key="schema-browser" icon={<TableOutlined />}>
              <Link to="/data-sync/datalake/schema-browser">
                {t('dataSync:datalake.nav.schemaBrowser', 'Schema 浏览器')}
              </Link>
            </Menu.Item>
          </Menu>
        </Card>

        <Outlet />
      </Space>
    </div>
  );
};

export default DatalakePage;
