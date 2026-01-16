// 500 Server Error page
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ROUTES } from '@/constants';

const ServerErrorPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation('common');

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Result
        status="500"
        title="500"
        subTitle={t('error.pages.serverError.subtitle')}
        extra={[
          <Button type="primary" key="home" onClick={() => navigate(ROUTES.HOME)}>
            {t('error.pages.serverError.backHome')}
          </Button>,
          <Button key="retry" onClick={() => window.location.reload()}>
            {t('error.pages.serverError.refresh')}
          </Button>,
        ]}
      />
    </div>
  );
};

export default ServerErrorPage;
