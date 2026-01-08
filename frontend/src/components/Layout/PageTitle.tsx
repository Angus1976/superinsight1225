// Page title component
import { Typography, Space, Button, Divider } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

interface PageTitleProps {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  backPath?: string;
  extra?: React.ReactNode;
  children?: React.ReactNode;
}

export const PageTitle: React.FC<PageTitleProps> = ({
  title,
  subtitle,
  showBack = false,
  backPath,
  extra,
  children,
}) => {
  const navigate = useNavigate();

  const handleBack = () => {
    if (backPath) {
      navigate(backPath);
    } else {
      navigate(-1);
    }
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: subtitle || children ? 16 : 0,
        }}
      >
        <Space align="center">
          {showBack && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
              style={{ marginRight: 8 }}
            />
          )}
          <Title level={2} style={{ margin: 0 }}>
            {title}
          </Title>
        </Space>
        {extra && <div>{extra}</div>}
      </div>

      {subtitle && (
        <Text type="secondary" style={{ fontSize: 16 }}>
          {subtitle}
        </Text>
      )}

      {children && (
        <div style={{ marginTop: 16 }}>
          {children}
        </div>
      )}

      <Divider style={{ margin: '16px 0' }} />
    </div>
  );
};