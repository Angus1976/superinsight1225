// Forgot password form component
import { useState } from 'react';
import { Form, Input, Button, message, Result } from 'antd';
import { MailOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { authService } from '@/services/auth';

interface ForgotPasswordFormProps {
  onBack?: () => void;
}

export const ForgotPasswordForm: React.FC<ForgotPasswordFormProps> = ({ onBack }) => {
  const { t } = useTranslation('auth');
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [email, setEmail] = useState('');

  const handleSubmit = async (values: { email: string }) => {
    setLoading(true);
    try {
      await authService.requestPasswordReset(values.email);
      setEmail(values.email);
      setEmailSent(true);
      message.success(t('forgotPassword.emailSent'));
    } catch (error) {
      message.error(t('forgotPassword.failed'));
    } finally {
      setLoading(false);
    }
  };

  if (emailSent) {
    return (
      <Result
        status="success"
        title={t('forgotPassword.emailSentTitle')}
        subTitle={t('forgotPassword.emailSentMessage', { email })}
        extra={[
          <Button key="back" onClick={onBack}>
            {t('forgotPassword.backToLogin')}
          </Button>,
          <Button key="resend" type="primary" onClick={() => setEmailSent(false)}>
            {t('forgotPassword.resendEmail')}
          </Button>,
        ]}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Button 
          type="text" 
          icon={<ArrowLeftOutlined />} 
          onClick={onBack}
          style={{ padding: 0 }}
        >
          {t('forgotPassword.backToLogin')}
        </Button>
      </div>

      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h2>{t('forgotPassword.title')}</h2>
        <p style={{ color: '#666', margin: 0 }}>
          {t('forgotPassword.subtitle')}
        </p>
      </div>

      <Form
        name="forgotPassword"
        onFinish={handleSubmit}
        size="large"
        layout="vertical"
      >
        <Form.Item
          name="email"
          rules={[
            { required: true, message: t('forgotPassword.emailRequired') },
            { type: 'email', message: t('forgotPassword.emailInvalid') },
          ]}
        >
          <Input 
            prefix={<MailOutlined />} 
            placeholder={t('forgotPassword.emailPlaceholder')} 
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            {t('forgotPassword.submit')}
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};