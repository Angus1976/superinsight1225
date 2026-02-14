import React, { useState, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Avatar,
  List,
  Tag,
  Spin,
  Empty,
  Divider,
  Row,
  Col,
  Statistic,
  message,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  BulbOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import './styles.css';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'text' | 'workflow' | 'analysis';
}

interface QuickAction {
  icon: React.ReactNode;
  title: string;
  description: string;
  prompt: string;
}

const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 快捷操作
  const quickActions: QuickAction[] = [
    {
      icon: <LineChartOutlined />,
      title: '销售预测分析',
      description: '基于历史数据预测未来销售趋势',
      prompt: '请根据最新的数据集，设计一个工作流，可以分析每日的销售预测，并根据实际销售额，实时修正预测能力。',
    },
    {
      icon: <ThunderboltOutlined />,
      title: '数据质量检查',
      description: '自动检查数据集的质量问题',
      prompt: '帮我分析当前数据集的质量，找出可能存在的问题，并给出改进建议。',
    },
    {
      icon: <BulbOutlined />,
      title: '智能标注建议',
      description: '基于 AI 提供标注建议',
      prompt: '请帮我分析未标注的数据，并提供智能标注建议。',
    },
    {
      icon: <ClockCircleOutlined />,
      title: '任务进度追踪',
      description: '查看和分析任务完成情况',
      prompt: '帮我分析当前所有任务的进度，找出可能延期的任务，并给出优化建议。',
    },
  ];

  const handleSendMessage = async () => {
    if (!inputValue.trim()) {
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // 模拟 AI 响应
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateResponse(inputValue),
        timestamp: new Date(),
        type: inputValue.includes('工作流') ? 'workflow' : 'text',
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const generateResponse = (input: string): string => {
    if (input.includes('销售预测') || input.includes('工作流')) {
      return `我已经为您设计了一个销售预测工作流：

**工作流步骤：**

1. **数据收集** 📊
   - 从数据库获取历史销售数据
   - 包含：日期、产品、销售额、地区等维度
   - 时间范围：最近 12 个月

2. **数据预处理** 🔧
   - 清洗异常值和缺失值
   - 特征工程：提取时间特征（星期、月份、季节）
   - 数据标准化

3. **模型训练** 🤖
   - 使用时间序列模型（ARIMA/Prophet）
   - 训练集：前 10 个月数据
   - 验证集：最近 2 个月数据

4. **预测生成** 📈
   - 生成未来 7 天的销售预测
   - 包含置信区间
   - 按产品和地区分组

5. **实时修正** ⚡
   - 每日对比实际销售额与预测值
   - 计算预测误差（MAPE）
   - 自动调整模型参数
   - 重新训练模型（增量学习）

6. **结果展示** 📊
   - 可视化预测趋势
   - 显示预测准确率
   - 生成分析报告

**预期效果：**
- 预测准确率：85%+
- 每日自动更新
- 支持多维度分析

是否需要我帮您创建这个工作流的具体配置？`;
    }

    if (input.includes('数据质量')) {
      return `我已经分析了您的数据集质量，以下是发现的问题和建议：

**质量问题：**
1. ⚠️ 缺失值：约 5% 的记录存在缺失字段
2. ⚠️ 重复数据：发现 120 条重复记录
3. ⚠️ 异常值：销售额字段存在 15 个异常值

**改进建议：**
1. 使用均值/中位数填充缺失值
2. 去除重复记录
3. 使用 IQR 方法处理异常值
4. 增加数据验证规则

需要我帮您执行这些优化吗？`;
    }

    return `我理解您的需求。让我帮您分析一下...

基于您的问题，我建议：
1. 首先查看相关数据集
2. 分析数据特征和分布
3. 设计合适的处理流程
4. 生成可视化报告

您想从哪一步开始？`;
  };

  const handleQuickAction = (prompt: string) => {
    setInputValue(prompt);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="ai-assistant-container">
      <Row gutter={16}>
        {/* 左侧：对话区域 */}
        <Col span={16}>
          <Card className="chat-card">
            <div className="chat-header">
              <Space>
                <Avatar size={40} icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>AI 智能助手</Title>
                  <Text type="secondary">OpenClaw 驱动</Text>
                </div>
              </Space>
              <Tag color="success">在线</Tag>
            </div>

            <Divider />

            <div className="messages-container">
              {messages.length === 0 ? (
                <Empty
                  image={<RobotOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
                  description={
                    <Space direction="vertical" size="large">
                      <Text>您好！我是 AI 智能助手，可以帮您：</Text>
                      <Space direction="vertical" align="start">
                        <Text>• 📊 分析数据和生成报告</Text>
                        <Text>• 🔄 设计和优化工作流</Text>
                        <Text>• 💡 提供智能建议</Text>
                        <Text>• 📈 预测和趋势分析</Text>
                      </Space>
                      <Text type="secondary">请选择下方的快捷操作或直接输入您的问题</Text>
                    </Space>
                  }
                />
              ) : (
                <List
                  dataSource={messages}
                  renderItem={(msg) => (
                    <div className={`message-item ${msg.role}`}>
                      <Space align="start" size={12}>
                        <Avatar
                          icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                          style={{
                            backgroundColor: msg.role === 'user' ? '#52c41a' : '#1890ff',
                          }}
                        />
                        <div className="message-content">
                          <div className="message-header">
                            <Text strong>{msg.role === 'user' ? '您' : 'AI 助手'}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {msg.timestamp.toLocaleTimeString()}
                            </Text>
                          </div>
                          <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                            {msg.content}
                          </Paragraph>
                          {msg.type === 'workflow' && (
                            <Space style={{ marginTop: 12 }}>
                              <Button type="primary" size="small">
                                创建工作流
                              </Button>
                              <Button size="small">查看详情</Button>
                            </Space>
                          )}
                        </div>
                      </Space>
                    </div>
                  )}
                />
              )}
              {isLoading && (
                <div className="message-item assistant">
                  <Space align="start" size={12}>
                    <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                    <Spin tip="AI 正在思考..." />
                  </Space>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题... (Shift+Enter 换行，Enter 发送)"
                autoSize={{ minRows: 2, maxRows: 6 }}
                disabled={isLoading}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSendMessage}
                loading={isLoading}
                disabled={!inputValue.trim()}
                style={{ marginTop: 8 }}
              >
                发送
              </Button>
            </div>
          </Card>
        </Col>

        {/* 右侧：快捷操作和统计 */}
        <Col span={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* 统计卡片 */}
            <Card title="今日统计">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="对话次数" value={messages.length / 2} suffix="次" />
                </Col>
                <Col span={12}>
                  <Statistic title="工作流创建" value={0} suffix="个" />
                </Col>
              </Row>
            </Card>

            {/* 快捷操作 */}
            <Card title="快捷操作">
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {quickActions.map((action, index) => (
                  <Card
                    key={index}
                    size="small"
                    hoverable
                    onClick={() => handleQuickAction(action.prompt)}
                    className="quick-action-card"
                  >
                    <Space>
                      <Avatar icon={action.icon} style={{ backgroundColor: '#1890ff' }} />
                      <div>
                        <Text strong>{action.title}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {action.description}
                        </Text>
                      </div>
                    </Space>
                  </Card>
                ))}
              </Space>
            </Card>

            {/* 使用提示 */}
            <Card title="💡 使用提示" size="small">
              <Space direction="vertical" size="small">
                <Text>• 使用自然语言描述您的需求</Text>
                <Text>• 可以要求 AI 设计工作流</Text>
                <Text>• 支持数据分析和预测</Text>
                <Text>• 可以实时修正和优化</Text>
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default AIAssistant;
