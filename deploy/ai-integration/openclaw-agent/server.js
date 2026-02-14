const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = 8080;

app.use(bodyParser.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'openclaw-agent',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    gateway_url: process.env.GATEWAY_URL,
    llm_provider: process.env.LLM_PROVIDER
  });
});

// Agent info endpoint
app.get('/api/info', (req, res) => {
  res.json({
    name: process.env.AGENT_NAME || 'SuperInsight Assistant',
    description: process.env.AGENT_DESCRIPTION || 'AI assistant for governed data',
    version: '1.0.0',
    llm: {
      provider: process.env.LLM_PROVIDER,
      model: process.env.LLM_MODEL,
      api_url: process.env.LLM_API_URL
    },
    language: {
      user_language: process.env.OPENCLAW_USER_LANGUAGE,
      locale: process.env.OPENCLAW_LOCALE
    }
  });
});

// Skills endpoint
app.get('/api/skills', (req, res) => {
  res.json({
    skills: [
      {
        name: 'superinsight-data-query',
        description: 'Query governed data from SuperInsight',
        status: 'active'
      }
    ]
  });
});

// Execute skill endpoint (mock)
app.post('/api/skills/execute', async (req, res) => {
  const { skill_name, parameters } = req.body;
  
  console.log(`Executing skill: ${skill_name}`, parameters);
  
  // Mock skill execution
  if (skill_name === 'superinsight-data-query') {
    try {
      // Simulate calling SuperInsight API
      const apiUrl = process.env.SUPERINSIGHT_API_URL;
      console.log(`Would call SuperInsight API: ${apiUrl}`);
      
      res.json({
        success: true,
        skill: skill_name,
        result: {
          message: '模拟数据查询成功',
          data: {
            records: 10,
            quality_score: 0.95
          }
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  } else {
    res.status(404).json({
      success: false,
      error: 'Skill not found'
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenClaw Agent (Mock) listening on port ${PORT}`);
  console.log(`Gateway URL: ${process.env.GATEWAY_URL}`);
  console.log(`SuperInsight API: ${process.env.SUPERINSIGHT_API_URL}`);
  console.log(`LLM Provider: ${process.env.LLM_PROVIDER}`);
  console.log(`Language: ${process.env.OPENCLAW_USER_LANGUAGE}`);
});
