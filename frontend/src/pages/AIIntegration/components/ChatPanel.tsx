/**
 * Chat Panel - 对话面板
 * Conversational interface for workflow design
 */

import React, { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Space, Tag, Spin } from 'antd';
import { SendOutlined, ClearOutlined, BulbOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TextArea } = Input;

interface ChatPanelProps {
  onSendMessage: (message: string) => void;
  generating: boolean;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onSendMessage, generating }) => {
  const { t } = useTranslation('aiIntegration');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || generating) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    onSendMessage(input);
    setInput('');
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
  };

  const handleExampleClick = (example: string) => {
    setInput(example);
  };

  return (
    <Card
      title={t('workflowPlayground.chat.title')}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 16 }}
    >
      {/* Messages Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          marginBottom: 16,
          padding: 8,
          background: '#fafafa',
          borderRadius: 4,
        }}
      >
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>
            <BulbOutlined style={{ fontSize: 32, marginBottom: 16 }} />
            <p>{t('workflowPlayground.chat.examples.title')}</p>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag
                color="blue"
                style={{ cursor: 'pointer', padding: '4px 12px' }}
                onClick={() => handleExampleClick(t('workflowPlayground.chat.examples.example1'))}
              >
                {t('workflowPlayground.chat.examples.example1')}
              </Tag>
              <Tag
                color="green"
                style={{ cursor: 'pointer', padding: '4px 12px' }}
                onClick={() => handleExampleClick(t('workflowPlayground.chat.examples.example2'))}
              >
                {t('workflowPlayground.chat.examples.example2')}
              </Tag>
              <Tag
                color="purple"
                style={{ cursor: 'pointer', padding: '4px 12px' }}
                onClick={() => handleExampleClick(t('workflowPlayground.chat.examples.example3'))}
              >
                {t('workflowPlayground.chat.examples.example3')}
              </Tag>
            </Space>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: 12,
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div
              style={{
                maxWidth: '80%',
                padding: '8px 12px',
                borderRadius: 8,
                background: msg.role === 'user' ? '#1890ff' : '#fff',
                color: msg.role === 'user' ? '#fff' : '#000',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {generating && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin tip={t('workflowPlayground.workflow.generating')} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <Space.Compact style={{ width: '100%' }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={t('workflowPlayground.chat.placeholder')}
          autoSize={{ minRows: 2, maxRows: 4 }}
          disabled={generating}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={generating}
          disabled={!input.trim()}
        >
          {t('workflowPlayground.chat.send')}
        </Button>
        <Button icon={<ClearOutlined />} onClick={handleClear} disabled={generating}>
          {t('workflowPlayground.chat.clear')}
        </Button>
      </Space.Compact>
    </Card>
  );
};

export default ChatPanel;
