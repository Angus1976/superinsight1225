const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = process.env.GATEWAY_PORT || 3000;

app.use(bodyParser.json());

// Compose 服务名为 openclaw-agent（与 container_name 无关）
const AGENT_URL = process.env.AGENT_URL || 'http://openclaw-agent:8080';
const SUPERINSIGHT_URL = process.env.SUPERINSIGHT_API_URL || 'http://app:8000';
const OPENCLAW_CORE_URL = (process.env.OPENCLAW_CORE_URL || '').replace(/\/$/, '');
const OPENCLAW_GATEWAY_TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN || '';

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get('/health', async (req, res) => {
  let agentOk = false;
  let coreOk = null;
  try {
    const r = await axios.get(`${AGENT_URL}/health`, { timeout: 3000 });
    agentOk = r.data?.status === 'healthy';
  } catch { /* ignore */ }

  if (OPENCLAW_CORE_URL) {
    coreOk = false;
    try {
      const r = await axios.get(`${OPENCLAW_CORE_URL}/healthz`, { timeout: 3000 });
      coreOk = r.status === 200;
    } catch { /* ignore */ }
  }

  res.json({
    status: 'healthy',
    service: 'openclaw-gateway',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    agent_connected: agentOk,
    openclaw_core_connected: coreOk,
  });
});

// ---------------------------------------------------------------------------
// Gateway info
// ---------------------------------------------------------------------------
app.get('/api/info', (req, res) => {
  res.json({
    name: 'OpenClaw Gateway',
    version: '2.1.0',
    upstream_openclaw: OPENCLAW_CORE_URL || null,
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
// Proxy: Chat — official OpenClaw Gateway (HTTP) when configured, else Agent
// ---------------------------------------------------------------------------
async function chatViaOpenClawCore(body) {
  const message = body.message || '';
  const systemPrompt = body.system_prompt || '';
  const messages = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }
  messages.push({ role: 'user', content: message });

  const headers = { 'Content-Type': 'application/json' };
  if (OPENCLAW_GATEWAY_TOKEN) {
    headers.Authorization = `Bearer ${OPENCLAW_GATEWAY_TOKEN}`;
  }

  const r = await axios.post(
    `${OPENCLAW_CORE_URL}/v1/chat/completions`,
    {
      model: 'openclaw/default',
      messages,
    },
    { headers, timeout: 120000 }
  );
  const choice = r.data?.choices?.[0]?.message;
  const reply = choice?.content ?? choice?.reasoning_content ?? '';
  return { success: true, reply };
}

app.post('/api/chat', async (req, res) => {
  if (OPENCLAW_CORE_URL) {
    try {
      const out = await chatViaOpenClawCore(req.body);
      return res.json(out);
    } catch (err) {
      console.warn('OpenClaw core chat failed, falling back to agent:', err.message);
    }
  }
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
  console.log(`SuperInsight OpenClaw compat gateway listening on port ${PORT}`);
  console.log(`OpenClaw core URL: ${OPENCLAW_CORE_URL || '(disabled — chat via agent)'}`);
  console.log(`Agent URL: ${AGENT_URL}`);
  console.log(`SuperInsight API: ${SUPERINSIGHT_URL}`);
});
