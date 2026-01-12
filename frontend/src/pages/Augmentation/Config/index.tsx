import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Divider, InputNumber, Slider } from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
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
      message.success('配置保存成功');
    },
    onError: () => {
      message.error('配置保存失败');
    },
  });

  const resetConfigMutation = useMutation({
    mutationFn: () => api.post('/api/v1/augmentation/config/reset'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-config'] });
      message.success('配置重置成功');
    },
    onError: () => {
      message.error('配置重置失败');
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
        title="数据增强配置"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              loading={resetConfigMutation.isPending}
            >
              重置默认
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => form.submit()}
              loading={updateConfigMutation.isPending}
            >
              保存配置
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
          <Card type="inner" title="文本增强配置" style={{ marginBottom: 16 }}>
            <Form.Item name={['textAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用文本增强</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'synonymReplacement']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>同义词替换</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomInsertion']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>随机插入</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomSwap']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>随机交换</span>
            </Form.Item>
            
            <Form.Item name={['textAugmentation', 'randomDeletion']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>随机删除</span>
            </Form.Item>
            
            <Form.Item
              name={['textAugmentation', 'augmentationRatio']}
              label="增强比例"
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
          <Card type="inner" title="图像增强配置" style={{ marginBottom: 16 }}>
            <Form.Item name={['imageAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用图像增强</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'rotation']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>旋转</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'flip']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>翻转</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'brightness']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>亮度调整</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'contrast']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>对比度调整</span>
            </Form.Item>
            
            <Form.Item name={['imageAugmentation', 'noise']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>添加噪声</span>
            </Form.Item>
            
            <Form.Item
              name={['imageAugmentation', 'augmentationRatio']}
              label="增强比例"
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
          <Card type="inner" title="音频增强配置" style={{ marginBottom: 16 }}>
            <Form.Item name={['audioAugmentation', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用音频增强</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'speedChange']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>速度变化</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'pitchShift']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>音调变化</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'addNoise']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>添加噪声</span>
            </Form.Item>
            
            <Form.Item name={['audioAugmentation', 'timeStretch']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>时间拉伸</span>
            </Form.Item>
            
            <Form.Item
              name={['audioAugmentation', 'augmentationRatio']}
              label="增强比例"
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
          <Card type="inner" title="通用配置">
            <Form.Item
              name={['general', 'maxAugmentationsPerSample']}
              label="每个样本最大增强数量"
            >
              <InputNumber min={1} max={10} />
            </Form.Item>
            
            <Form.Item name={['general', 'preserveOriginal']} valuePropName="checked">
              <Switch />
              <span style={{ marginLeft: 8 }}>保留原始样本</span>
            </Form.Item>
            
            <Form.Item
              name={['general', 'qualityThreshold']}
              label="质量阈值"
              help="低于此阈值的增强样本将被丢弃"
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