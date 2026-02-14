const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.GATEWAY_PORT || 3000;

app.use(bodyParser.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'openclaw-gateway',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Gateway info endpoint
app.get('/api/info', (req, res) => {
  res.json({
    name: 'OpenClaw Gateway (Mock)',
    version: '1.0.0',
    superinsight_api: process.env.SUPERINSIGHT_API_URL,
    tenant_id: process.env.SUPERINSIGHT_TENANT_ID
  });
});

// Message routing endpoint (mock)
app.post('/api/messages', (req, res) => {
  console.log('Received message:', req.body);
  res.json({
    success: true,
    message_id: `msg_${Date.now()}`,
    status: 'queued'
  });
});

// Channel status endpoint
app.get('/api/channels', (req, res) => {
  res.json({
    channels: [
      { name: 'console', status: 'active', type: 'test' }
    ]
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenClaw Gateway (Mock) listening on port ${PORT}`);
  console.log(`SuperInsight API: ${process.env.SUPERINSIGHT_API_URL}`);
  console.log(`Tenant ID: ${process.env.SUPERINSIGHT_TENANT_ID}`);
});
