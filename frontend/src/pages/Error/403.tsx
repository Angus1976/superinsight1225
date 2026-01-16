// 403 Forbidden page
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ROUTES } from '@/constants';

const ForbiddenPage: React.FC = () => {
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
        status="403"
        title={t('error.pages.forbidden.title')}
        subTitle={t('error.pages.forbidden.subtitle')}
        extra={
          <Button type="primary" onClick={() => navigate(ROUTES.HOME)}>
            {t('error.pages.forbidden.backHome')}
          </Button>
        }
      />
    </div>
  );
};

export default ForbiddenPage;
