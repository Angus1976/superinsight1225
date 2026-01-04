import React, { useState, useEffect } from 'react';

// 简单的登录组件
const SimpleLogin: React.FC = () => {
  const [username, setUsername] = useState('admin_test');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | ''>('');
  const [systemStatus, setSystemStatus] = useState({
    backend: '检查中...',
    database: '检查中...',
    auth: '就绪'
  });

  // 检查系统状态
  const checkSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      if (response.ok) {
        setSystemStatus({
          backend: '✅ 正常',
          database: '✅ 已连接',
          auth: '✅ 就绪'
        });
      } else {
        throw new Error('Backend not responding');
      }
    } catch (error) {
      setSystemStatus({
        backend: '❌ 离线',
        database: '❌ 未连接',
        auth: '✅ 就绪'
      });
    }
  };

  // 登录处理
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/api/security/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`登录成功！欢迎 ${data.user.full_name} (${data.user.role})`);
        setMessageType('success');
        
        // 存储 token
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user_info', JSON.stringify(data.user));
        
        // 显示成功信息
        setTimeout(() => {
          setMessage('登录成功！系统已准备就绪。');
        }, 2000);
      } else {
        setMessage(data.detail || '登录失败，请检查用户名和密码');
        setMessageType('error');
      }
    } catch (error) {
      setMessage('网络错误，请检查后端服务是否运行');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  // 填充测试账号
  const fillAccount = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
  };

  // 页面加载时检查系统状态
  useEffect(() => {
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const accounts = [
    { name: '系统管理员', role: 'ADMIN - 完全访问权限', username: 'admin_test', password: 'admin123' },
    { name: '业务专家', role: 'BUSINESS_EXPERT - 数据分析', username: 'expert_test', password: 'expert123' },
    { name: '数据标注员', role: 'ANNOTATOR - 数据标注', username: 'annotator_test', password: 'annotator123' },
    { name: '报表查看者', role: 'VIEWER - 报表查看', username: 'viewer_test', password: 'viewer123' }
  ];

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '400px'
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#333', fontSize: '28px', fontWeight: '600', margin: 0 }}>
            SuperInsight
          </h1>
          <p style={{ color: '#666', marginTop: '8px', margin: 0 }}>
            企业级 AI 数据治理与标注平台
          </p>
        </div>

        {/* 登录表单 */}
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#333', fontWeight: '500' }}>
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '2px solid #e1e5e9',
                borderRadius: '8px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              required
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#333', fontWeight: '500' }}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '2px solid #e1e5e9',
                borderRadius: '8px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px',
              background: loading ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        {/* 消息显示 */}
        {message && (
          <div style={{
            marginTop: '20px',
            padding: '12px',
            borderRadius: '6px',
            textAlign: 'center',
            background: messageType === 'success' ? '#d4edda' : '#f8d7da',
            color: messageType === 'success' ? '#155724' : '#721c24',
            border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
          }}>
            {message}
          </div>
        )}

        {/* 系统状态 */}
        <div style={{
          marginTop: '20px',
          padding: '15px',
          background: '#e7f3ff',
          borderRadius: '6px',
          borderLeft: '4px solid #007bff'
        }}>
          <h4 style={{ color: '#0056b3', marginBottom: '8px', margin: 0 }}>系统状态</h4>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '4px 0', fontSize: '14px' }}>
            <span>后端 API:</span>
            <span dangerouslySetInnerHTML={{ __html: systemStatus.backend }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '4px 0', fontSize: '14px' }}>
            <span>数据库:</span>
            <span dangerouslySetInnerHTML={{ __html: systemStatus.database }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '4px 0', fontSize: '14px' }}>
            <span>认证系统:</span>
            <span dangerouslySetInnerHTML={{ __html: systemStatus.auth }} />
          </div>
        </div>

        {/* 测试账号 */}
        <div style={{
          marginTop: '30px',
          padding: '20px',
          background: '#f8f9fa',
          borderRadius: '8px'
        }}>
          <h3 style={{ color: '#333', marginBottom: '15px', fontSize: '16px', margin: '0 0 15px 0' }}>
            测试账号
          </h3>
          {accounts.map((account, index) => (
            <div
              key={index}
              onClick={() => fillAccount(account.username, account.password)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: index < accounts.length - 1 ? '1px solid #e9ecef' : 'none',
                cursor: 'pointer'
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '500', color: '#333' }}>{account.name}</div>
                <div style={{ fontSize: '12px', color: '#666' }}>{account.role}</div>
              </div>
              <div style={{ fontSize: '12px', color: '#007bff' }}>
                {account.username} / {account.password}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SimpleLogin;