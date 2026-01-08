// Reset password form component
import { useState } from 'react';
import { Form, Input, Button, message, Result } from 'antd';
import { LockOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '@/services/auth';
import { ROUTES } from '@/constants';

export const ResetPasswordForm: React.FC = () => {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const token = searchParams.get('token');
  const email = searchParams.get('email');

  const handleSubmit = async (values: { password: string; confirmPassword: string }) => {
    if (!token || !email) {
      message.error(t('resetPassword.invalidLink'));
      return;
    }

    setLoading(true);
    try {
      await authService.resetPassword({
        token,
        email,
        password: values.password,
      });
      setResetSuccess(true);
      message.success(t('resetPassword.success'));
    } catch (error) {
      message.error(t('resetPassword.failed'));
    } finally {
      setLoading(false);
    }
  };

  if (!token || !email) {
    return (
      <Result
        status="error"
        title={t('resetPassword.invalidLinkTitle')}
        subTitle={t('resetPassword.invalidLinkMessage')}
        extra={
          <Button type="primary" onClick={() => navigate(ROUTES.LOGIN)}>
            {t('resetPassword.backToLogin')}
          </Button>
        }
      />
    );
  }

  if (resetSuccess) {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title={t('resetPassword.successTitle')}
        subTitle={t('resetPassword.successMessage')}
        extra={
          <Button type="primary" onClick={() => navigate(ROUTES.LOGIN)}>
            {t('resetPassword.goToLogin')}
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h2>{t('resetPassword.title')}</h2>
        <p style={{ color: '#666', margin: 0 }}>
          {t('resetPassword.subtitle')}
        </p>
      </div>

      <Form
        name="resetPassword"
        onFinish={handleSubmit}
        size="large"
        layout="vertical"
      >
        <Form.Item
          name="password"
          rules={[
            { required: true, message: t('resetPassword.passwordRequired') },
            { min: 8, message: t('resetPassword.passwordLength') },
          ]}
        >
          <Input.Password 
            prefix={<LockOutlined />} 
            placeholder={t('resetPassword.passwordPlaceholder')} 
          />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          dependencies={['password']}
          rules={[
            { required: true, message: t('resetPassword.confirmPasswordRequired') },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error(t('resetPassword.passwordMismatch')));
              },
            }),
          ]}
        >
          <Input.Password 
            prefix={<LockOutlined />} 
            placeholder={t('resetPassword.confirmPasswordPlaceholder')} 
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            {t('resetPassword.submit')}
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};