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
import {
  activationApi,
  ActivationResult,
  OfflineActivationRequest,
} from '../../services/licenseApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

type ActivationMode = 'online' | 'offline';

const ActivationWizard: React.FC = () => {
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
        message.success('许可证激活成功！');
      } else {
        setError(result.error || '激活失败');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '激活请求失败';
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
      const errorMessage = err instanceof Error ? err.message : '生成离线请求失败';
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
        message.success('许可证激活成功！');
      } else {
        setError(result.error || '激活失败');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '激活请求失败';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
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
            <Title level={4}>选择激活方式</Title>
            <Paragraph type="secondary">
              请根据您的网络环境选择合适的激活方式
            </Paragraph>
            <Space size="large" style={{ marginTop: 24 }}>
              <Card
                hoverable
                style={{ width: 240, textAlign: 'center' }}
                onClick={() => handleModeSelect('online')}
              >
                <CloudOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <Title level={5}>在线激活</Title>
                <Text type="secondary">
                  需要网络连接，自动完成激活
                </Text>
              </Card>
              <Card
                hoverable
                style={{ width: 240, textAlign: 'center' }}
                onClick={() => handleModeSelect('offline')}
              >
                <DesktopOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                <Title level={5}>离线激活</Title>
                <Text type="secondary">
                  无需网络，手动输入激活码
                </Text>
              </Card>
            </Space>
          </div>
        );

      case 1:
        return (
          <div style={{ maxWidth: 500, margin: '0 auto', padding: '24px 0' }}>
            <Title level={4}>
              {activationMode === 'online' ? '在线激活' : '离线激活 - 步骤 1'}
            </Title>
            
            {error && (
              <Alert
                message="激活错误"
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
                label="许可证密钥"
                rules={[
                  { required: true, message: '请输入许可证密钥' },
                  { pattern: /^[A-Z0-9-]+$/, message: '许可证密钥格式不正确' },
                ]}
              >
                <Input
                  prefix={<KeyOutlined />}
                  placeholder="XXXX-XXXX-XXXX-XXXX"
                  size="large"
                />
              </Form.Item>

              <Form.Item label="硬件指纹">
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
                    复制
                  </Button>
                </Input.Group>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  硬件指纹用于绑定许可证到此设备
                </Text>
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button onClick={() => setCurrentStep(0)}>
                    上一步
                  </Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    {activationMode === 'online' ? '激活' : '生成请求码'}
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
              <Title level={4}>离线激活 - 步骤 2</Title>
              <Paragraph>
                请将以下请求码发送给许可证管理员，获取激活码后继续。
              </Paragraph>

              <Card style={{ marginBottom: 16 }}>
                <Form.Item label="请求码">
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
                      复制
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={downloadRequestCode}
                    >
                      下载
                    </Button>
                  </Space>
                </Form.Item>
                <Text type="secondary">
                  请求码有效期至: {new Date(offlineRequest.expires_at).toLocaleString()}
                </Text>
              </Card>

              <Divider>输入激活码</Divider>

              {error && (
                <Alert
                  message="激活错误"
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
                  label="激活码"
                  rules={[{ required: true, message: '请输入激活码' }]}
                >
                  <TextArea
                    placeholder="请粘贴从许可证管理员获取的激活码"
                    rows={4}
                  />
                </Form.Item>

                <Form.Item>
                  <Space>
                    <Button onClick={() => setCurrentStep(1)}>
                      上一步
                    </Button>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      激活
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
            title="许可证激活成功！"
            subTitle={
              activationResult?.license && (
                <div>
                  <p>许可证类型: {activationResult.license.license_type}</p>
                  <p>有效期至: {new Date(activationResult.license.validity_end).toLocaleDateString()}</p>
                </div>
              )
            }
            extra={[
              <Button type="primary" key="dashboard" onClick={() => navigate('/license')}>
                查看许可证详情
              </Button>,
              <Button key="home" onClick={() => navigate('/')}>
                返回首页
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
          <KeyOutlined /> 许可证激活向导
        </Title>

        <Steps
          current={currentStep}
          style={{ marginBottom: 32 }}
          items={[
            { title: '选择方式' },
            { title: '输入密钥' },
            ...(activationMode === 'offline' ? [{ title: '获取激活码' }] : []),
            { title: '完成' },
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
