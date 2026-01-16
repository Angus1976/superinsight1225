import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Divider, InputNumber, Slider } from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface AugmentationConfig {
  textAugmentation: {
    enabled: boolean;
    synonymReplacement: boolean;
    randomInsertion: boolean;
    randomSwap: boolean;
    randomDeletion: boolean;
    augmentationRatio: number;
  };
  imageAugmentation: {
    enabled: boolean;
    rotation: boolean;
    flip: boolean;
    brightness: boolean;
    contrast: boolean;
    noise: boolean;
    augmentationRatio: number;
  };
  audioAugmentation: {
    enabled: boolean;
    speedChange: boolean;
    pitchShift: boolean;
    addNoise: boolean;
    timeStretch: boolean;
    augmentationRatio: number;
  };
  general: {
    maxAugmentationsPerSample: number;
    preserveOriginal: boolean;
    qualityThreshold: number;
  };
}

const AugmentationConfig: React.FC = () => {
  const { t } = useTranslation('augmentation');
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['augmentation-config'],
    queryFn: () => api.get('/api/v1/augmentation/config').then(res => res.data),
  });

  const updateConfigMutation = useMutation({
    mutationFn: (data: AugmentationConfig) => api.put('/api/v1/augmentation/config', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-config'] });
      message.success(t('config.saveSuccess'));
    },
    onError: () => {
      message.error(t('config.saveFailed'));
    },
  });

  const resetConfigMutation = useMutation({
    mutationFn: () => api.post('/api/v1/augmentation/config/reset'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-config'] });
      message.success(t('config.resetSuccess'));
    },
    onError: () => {
      message.error(t('config.resetFailed'));
    },
  });

  const handleSubmit = (values: AugmentationConfig) => {
    updateConfigMutation.mutate(values);
  };

  const handleReset = () => {
    resetConfigMutation.mutate();
  };

  React.useEffect(() => {
    if (config) {
      form.setFieldsValue(config);
    }
  }, [config, form]);

  return (
    <div className="augmentation-config">
      <Card
        title={t('config.title')}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              loading={resetConfigMutation.isPending}
            >
              {t('config.resetDefault')}
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => form.submit()}
              loading={updateConfigMutation.isPending}
            >
              {t('config.saveConfig')}
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          loading={isLoading}
        >
          {/* 文本增强配置 */}
          <Card type="inner" title={t('config.textAugmentation.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['textAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('config.switch.enabled')} unCheckedChildren={t('config.switch.disabled')} />
              <span style={{ marginLeft: 8 }}>{t('config.textAugmentation.enabled')}</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'synonymReplacement']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.textAugmentation.synonymReplacement')}</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomInsertion']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.textAugmentation.randomInsertion')}</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomSwap']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.textAugmentation.randomSwap')}</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomDeletion']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.textAugmentation.randomDeletion')}</span>
            </Form.Item>
            
            <Form.Item
              name={['textAugmentation', 'augmentationRatio']}
              label={t('config.textAugmentation.augmentationRatio')}
            >
              <Slider
                min={0.1}
                max={2.0}
                step={0.1}
                marks={{
                  0.1: '0.1x',
                  1.0: '1.0x',
                  2.0: '2.0x',
                }}
              />
            </Form.Item>
          </Card>

          {/* 图像增强配置 */}
          <Card type="inner" title={t('config.imageAugmentation.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['imageAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('config.switch.enabled')} unCheckedChildren={t('config.switch.disabled')} />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.enabled')}</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'rotation']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.rotation')}</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'flip']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.flip')}</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'brightness']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.brightness')}</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'contrast']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.contrast')}</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'noise']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.imageAugmentation.noise')}</span>
            </Form.Item>
            
            <Form.Item
              name={['imageAugmentation', 'augmentationRatio']}
              label={t('config.imageAugmentation.augmentationRatio')}
            >
              <Slider
                min={0.1}
                max={2.0}
                step={0.1}
                marks={{
                  0.1: '0.1x',
                  1.0: '1.0x',
                  2.0: '2.0x',
                }}
              />
            </Form.Item>
          </Card>

          {/* 音频增强配置 */}
          <Card type="inner" title={t('config.audioAugmentation.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['audioAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('config.switch.enabled')} unCheckedChildren={t('config.switch.disabled')} />
              <span style={{ marginLeft: 8 }}>{t('config.audioAugmentation.enabled')}</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'speedChange']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.audioAugmentation.speedChange')}</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'pitchShift']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.audioAugmentation.pitchShift')}</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'addNoise']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.audioAugmentation.addNoise')}</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'timeStretch']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.audioAugmentation.timeStretch')}</span>
            </Form.Item>
            
            <Form.Item
              name={['audioAugmentation', 'augmentationRatio']}
              label={t('config.audioAugmentation.augmentationRatio')}
            >
              <Slider
                min={0.1}
                max={2.0}
                step={0.1}
                marks={{
                  0.1: '0.1x',
                  1.0: '1.0x',
                  2.0: '2.0x',
                }}
              />
            </Form.Item>
          </Card>

          {/* 通用配置 */}
          <Card type="inner" title={t('config.general.title')}>
            <Form.Item
              name={['general', 'maxAugmentationsPerSample']}
              label={t('config.general.maxAugmentationsPerSample')}
            >
              <InputNumber min={1} max={10} />
            </Form.Item>
            
            <Form.Item name={['general', 'preserveOriginal']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>{t('config.general.preserveOriginal')}</span>
            </Form.Item>
            
            <Form.Item
              name={['general', 'qualityThreshold']}
              label={t('config.general.qualityThreshold')}
              help={t('config.general.qualityThresholdHelp')}
            >
              <Slider
                min={0.1}
                max={1.0}
                step={0.1}
                marks={{
                  0.1: '0.1',
                  0.5: '0.5',
                  1.0: '1.0',
                }}
              />
            </Form.Item>
          </Card>
        </Form>
      </Card>
    </div>
  );
};

export default AugmentationConfig;
