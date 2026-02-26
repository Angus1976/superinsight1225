const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = process.env.GATEWAY_PORT || 3000;

app.use(bodyParser.json());

const AGENT_URL = process.env.AGENT_URL || 'http://superinsight-openclaw-agent:8080';
const SUPERINSIGHT_URL = process.env.SUPERINSIGHT_API_URL || 'http://app:8000';

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get('/health', async (req, res) => {
  let agentOk = false;
  try {
    const r = await axios.get(`${AGENT_URL}/health`, { timeout: 3000 });
    agentOk = r.data?.status === 'healthy';
  } catch { /* ignore */ }

  res.json({
    status: 'healthy',
    service: 'openclaw-gateway',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    agent_connected: agentOk,
  });
});

// ---------------------------------------------------------------------------
// Gateway info
// ---------------------------------------------------------------------------
app.get('/api/info', (req, res) => {
  res.json({
    name: 'OpenClaw Gateway',
    version: '2.0.0',
    superinsight_api: SUPERINSIGHT_URL,
    tenant_id: process.env.SUPERINSIGHT_TENANT_ID,
  });
});

// ---------------------------------------------------------------------------
// Proxy: Skills (forward to Agent)
// ---------------------------------------------------------------------------
app.get('/api/skills', async (req, res) => {
  try {
    const r = await axios.get(`${AGENT_URL}/api/skills`, { timeout: 5000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

app.get('/api/skills/catalog', async (req, res) => {
  try {
    const r = await axios.get(`${AGENT_URL}/api/skills/catalog`, { timeout: 5000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

app.post('/api/skills/deploy', async (req, res) => {
  try {
    const r = await axios.post(`${AGENT_URL}/api/skills/deploy`, req.body, { timeout: 5000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

app.post('/api/skills/undeploy', async (req, res) => {
  try {
    const r = await axios.post(`${AGENT_URL}/api/skills/undeploy`, req.body, { timeout: 5000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

app.post('/api/skills/execute', async (req, res) => {
  try {
    const r = await axios.post(`${AGENT_URL}/api/skills/execute`, req.body, { timeout: 120000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

// ---------------------------------------------------------------------------
// Proxy: Chat (forward to Agent)
// ---------------------------------------------------------------------------
app.post('/api/chat', async (req, res) => {
  try {
    const r = await axios.post(`${AGENT_URL}/api/chat`, req.body, { timeout: 120000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

// ---------------------------------------------------------------------------
// Proxy: LLM status
// ---------------------------------------------------------------------------
app.get('/api/llm/status', async (req, res) => {
  try {
    const r = await axios.get(`${AGENT_URL}/api/llm/status`, { timeout: 5000 });
    res.json(r.data);
  } catch (err) {
    res.status(502).json({ error: 'Agent 不可用', detail: err.message });
  }
});

// ---------------------------------------------------------------------------
// Message routing (legacy)
// ---------------------------------------------------------------------------
app.post('/api/messages', (req, res) => {
  console.log('Received message:', req.body);
  res.json({ success: true, message_id: `msg_${Date.now()}`, status: 'queued' });
});

// Channel status
app.get('/api/channels', (req, res) => {
  res.json({ channels: [{ name: 'console', status: 'active', type: 'test' }] });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenClaw Gateway v2.0 listening on port ${PORT}`);
  console.log(`Agent URL: ${AGENT_URL}`);
  console.log(`SuperInsight API: ${SUPERINSIGHT_URL}`);
});
