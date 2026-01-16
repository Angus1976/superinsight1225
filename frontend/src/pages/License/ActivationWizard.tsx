/**
 * License Activation Wizard
 * 
 * Step-by-step wizard for activating licenses online or offline.
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Steps,
  Form,
  Input,
  Button,
  Radio,
  Result,
  Alert,
  Space,
  Typography,
  Spin,
  Divider,
  message,
} from 'antd';
import {
  KeyOutlined,
  CloudOutlined,
  DesktopOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  activationApi,
  ActivationResult,
  OfflineActivationRequest,
} from '../../services/licenseApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

type ActivationMode = 'online' | 'offline';

const ActivationWizard: React.FC = () => {
  const { t } = useTranslation(['license', 'common']);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [activationMode, setActivationMode] = useState<ActivationMode>('online');
  const [loading, setLoading] = useState(false);
  const [hardwareFingerprint, setHardwareFingerprint] = useState<string>('');
  const [offlineRequest, setOfflineRequest] = useState<OfflineActivationRequest | null>(null);
  const [activationResult, setActivationResult] = useState<ActivationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch hardware fingerprint on mount
  useEffect(() => {
    const fetchFingerprint = async () => {
      try {
        const result = await activationApi.getHardwareFingerprint();
        setHardwareFingerprint(result.fingerprint);
      } catch (err) {
        console.error('Failed to get hardware fingerprint:', err);
      }
    };
    fetchFingerprint();
  }, []);

  const handleModeSelect = (mode: ActivationMode) => {
    setActivationMode(mode);
    setCurrentStep(1);
  };

  const handleOnlineActivation = async (values: { license_key: string }) => {
    setLoading(true);
    setError(null);
    try {
      const result = await activationApi.activateOnline({
        license_key: values.license_key,
        hardware_fingerprint: hardwareFingerprint,
      });
      setActivationResult(result);
      if (result.success) {
        setCurrentStep(3);
        message.success(t('activation.activationSuccess'));
      } else {
        setError(result.error || t('activation.activationFailed'));
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('activation.activationRequestFailed');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateOfflineRequest = async (values: { license_key: string }) => {
    setLoading(true);
    setError(null);
    try {
      const request = await activationApi.generateOfflineRequest(
        values.license_key,
        hardwareFingerprint
      );
      setOfflineRequest(request);
      setCurrentStep(2);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('activation.generateRequestFailed');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleOfflineActivation = async (values: { activation_code: string }) => {
    setLoading(true);
    setError(null);
    try {
      const result = await activationApi.activateOffline(values.activation_code);
      setActivationResult(result);
      if (result.success) {
        setCurrentStep(3);
        message.success(t('activation.activationSuccess'));
      } else {
        setError(result.error || t('activation.activationFailed'));
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('activation.activationRequestFailed');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success(t('activation.copiedToClipboard'));
  };

  const downloadRequestCode = () => {
    if (!offlineRequest) return;
    const blob = new Blob([offlineRequest.request_code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'activation_request.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Title level={4}>{t('activation.selectMode')}</Title>
            <Paragraph type="secondary">
              {t('activation.selectModeHint')}
            </Paragraph>
            <Space size="large" style={{ marginTop: 24 }}>
              <Card
                hoverable
                style={{ width: 240, textAlign: 'center' }}
                onClick={() => handleModeSelect('online')}
              >
                <CloudOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <Title level={5}>{t('activation.onlineActivation')}</Title>
                <Text type="secondary">
                  {t('activation.onlineActivationDesc')}
                </Text>
              </Card>
              <Card
                hoverable
                style={{ width: 240, textAlign: 'center' }}
                onClick={() => handleModeSelect('offline')}
              >
                <DesktopOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                <Title level={5}>{t('activation.offlineActivation')}</Title>
                <Text type="secondary">
                  {t('activation.offlineActivationDesc')}
                </Text>
              </Card>
            </Space>
          </div>
        );

      case 1:
        return (
          <div style={{ maxWidth: 500, margin: '0 auto', padding: '24px 0' }}>
            <Title level={4}>
              {activationMode === 'online' ? t('activation.onlineActivation') : t('activation.offlineStep1')}
            </Title>
            
            {error && (
              <Alert
                message={t('activation.activationError')}
                description={error}
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
                closable
                onClose={() => setError(null)}
              />
            )}

            <Form
              form={form}
              layout="vertical"
              onFinish={activationMode === 'online' ? handleOnlineActivation : handleGenerateOfflineRequest}
            >
              <Form.Item
                name="license_key"
                label={t('activation.licenseKey')}
                rules={[
                  { required: true, message: t('activation.enterLicenseKey') },
                  { pattern: /^[A-Z0-9-]+$/, message: t('activation.invalidKeyFormat') },
                ]}
              >
                <Input
                  prefix={<KeyOutlined />}
                  placeholder="XXXX-XXXX-XXXX-XXXX"
                  size="large"
                />
              </Form.Item>

              <Form.Item label={t('activation.hardwareFingerprint')}>
                <Input.Group compact>
                  <Input
                    value={hardwareFingerprint}
                    readOnly
                    style={{ width: 'calc(100% - 80px)' }}
                  />
                  <Button
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(hardwareFingerprint)}
                  >
                    {t('activation.copy')}
                  </Button>
                </Input.Group>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('activation.hardwareFingerprintHint')}
                </Text>
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button onClick={() => setCurrentStep(0)}>
                    {t('activation.previousStep')}
                  </Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    {activationMode === 'online' ? t('activation.activate') : t('activation.generateRequestCode')}
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        );

      case 2:
        if (activationMode === 'offline' && offlineRequest) {
          return (
            <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 0' }}>
              <Title level={4}>{t('activation.offlineStep2')}</Title>
              <Paragraph>
                {t('activation.requestCodeHint')}
              </Paragraph>

              <Card style={{ marginBottom: 16 }}>
                <Form.Item label={t('activation.requestCode')}>
                  <TextArea
                    value={offlineRequest.request_code}
                    readOnly
                    rows={4}
                  />
                  <Space style={{ marginTop: 8 }}>
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() => copyToClipboard(offlineRequest.request_code)}
                    >
                      {t('activation.copy')}
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={downloadRequestCode}
                    >
                      {t('activation.download')}
                    </Button>
                  </Space>
                </Form.Item>
                <Text type="secondary">
                  {t('activation.requestCodeExpiry')}: {new Date(offlineRequest.expires_at).toLocaleString()}
                </Text>
              </Card>

              <Divider>{t('activation.enterActivationCode')}</Divider>

              {error && (
                <Alert
                  message={t('activation.activationError')}
                  description={error}
                  type="error"
                  showIcon
                  style={{ marginBottom: 16 }}
                  closable
                  onClose={() => setError(null)}
                />
              )}

              <Form
                layout="vertical"
                onFinish={handleOfflineActivation}
              >
                <Form.Item
                  name="activation_code"
                  label={t('activation.activationCode')}
                  rules={[{ required: true, message: t('activation.enterLicenseKey') }]}
                >
                  <TextArea
                    placeholder={t('activation.enterActivationCodePlaceholder')}
                    rows={4}
                  />
                </Form.Item>

                <Form.Item>
                  <Space>
                    <Button onClick={() => setCurrentStep(1)}>
                      {t('activation.previousStep')}
                    </Button>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      {t('activation.activate')}
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </div>
          );
        }
        return null;

      case 3:
        return (
          <Result
            status="success"
            icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            title={t('activation.activationSuccess')}
            subTitle={
              activationResult?.license && (
                <div>
                  <p>{t('dashboard.licenseType')}: {activationResult.license.license_type}</p>
                  <p>{t('dashboard.validityStatus')}: {new Date(activationResult.license.validity_end).toLocaleDateString()}</p>
                </div>
              )
            }
            extra={[
              <Button type="primary" key="dashboard" onClick={() => navigate('/license')}>
                {t('activation.viewLicenseDetails')}
              </Button>,
              <Button key="home" onClick={() => navigate('/')}>
                {t('activation.backToHome')}
              </Button>,
            ]}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2} style={{ textAlign: 'center', marginBottom: 32 }}>
          <KeyOutlined /> {t('activation.title')}
        </Title>

        <Steps
          current={currentStep}
          style={{ marginBottom: 32 }}
          items={[
            { title: t('activation.steps.selectMode') },
            { title: t('activation.steps.enterKey') },
            ...(activationMode === 'offline' ? [{ title: t('activation.steps.getActivationCode') }] : []),
            { title: t('activation.steps.complete') },
          ]}
        />

        <Spin spinning={loading}>
          {renderStepContent()}
        </Spin>
      </Card>
    </div>
  );
};

export default ActivationWizard;
