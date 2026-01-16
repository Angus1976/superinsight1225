// 404 Not Found page
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ROUTES } from '@/constants';

const NotFoundPage: React.FC = () => {
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
        status="404"
        title={t('error.pages.notFound.title')}
        subTitle={t('error.pages.notFound.subtitle')}
        extra={
          <Button type="primary" onClick={() => navigate(ROUTES.HOME)}>
            {t('error.pages.notFound.backHome')}
          </Button>
        }
      />
    </div>
  );
};

export default NotFoundPage;
