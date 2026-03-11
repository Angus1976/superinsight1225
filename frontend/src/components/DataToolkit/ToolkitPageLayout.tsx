import React from 'react';
import { Typography } from 'antd';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;

interface ToolkitPageLayoutProps {
  titleKey: string;
  descriptionKey?: string;
  children: React.ReactNode;
  extra?: React.ReactNode;
}

export const ToolkitPageLayout: React.FC<ToolkitPageLayoutProps> = ({
  titleKey,
  descriptionKey,
  children,
  extra,
}) => {
  const { t } = useTranslation('dataToolkit');

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>{t(titleKey)}</Title>
          {descriptionKey && (
            <Text type="secondary">{t(descriptionKey)}</Text>
          )}
        </div>
        {extra && <div>{extra}</div>}
      </div>
      {children}
    </div>
  );
};
