# SuperInsight Skill for OpenClaw - Complete Guide

**Version**: 2.0.0  
**Last Updated**: 2026-02-04  
**Requirements**: 14.1, 14.5

---

## Overview

The SuperInsight Skill enables conversational access to governed data through OpenClaw, with enhanced workflow design capabilities. Users can query data, design processing workflows, execute them, and compare quality metrics between governed and raw data - all through natural language.

## Key Features

### Data Querying (v1.0)
- Natural language query parsing
- Multi-tenant data access with authentication
- Channel-appropriate formatting (WhatsApp, Telegram, Slack, Discord)
- Pagination and filtering support

### Workflow Design (v2.0)
- **Conversational workflow creation**: Design data workflows through chat
- **Workflow execution**: Run workflows on governed data
- **Quality comparison**: Compare governed vs raw data results
- **Real-time feedback**: Get immediate quality metrics and insights

---

## Conversation Patterns

### Pattern 1: Data Query

**User Intent**: Query governed data with filters

```
User: Show me annotated data from dataset customer_reviews

Skill: Found 150 records (page 1):
       • ID: abc123 | Status: completed | Quality: 95.2%
       • ID: def456 | Status: completed | Quality: 92.8%
       • ID: ghi789 | Status: completed | Quality: 91.5%
       • ID: jkl012 | Status: completed | Quality: 94.0%
       • ID: mno345 | Status: completed | Quality: 93.7%
       
       Page 1 of 30
```

**Variations**:
- "Get data with quality score above 0.9"
- "Show me the first 10 pending annotations"
- "Query dataset product_images with quality: 0.85"

---

### Pattern 2: Workflow Design

**User Intent**: Create a data processing workflow

```
User: Design a workflow to analyze customer sentiment from reviews dataset, 
      filter by quality score above 0.9, and export as JSON

Skill: ✅ Workflow designed successfully!

       📋 Name: Customer Sentiment Analysis
       🆔 ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

       📊 Data Sources:
         • reviews (quality > 0.9)

       ⚙️ Processing Steps:
         1. filter: Select records with quality_score > 0.9
         2. transform: Extract sentiment features
         3. analyze: Calculate sentiment scores
         4. aggregate: Group by product category

       📤 Output: JSON

       💡 To execute: "execute workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890"
       📊 To compare: "compare workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**Variations**:
- "Create a workflow to clean and validate product data"
- "Design a pipeline for image annotation quality checks"
- "Build a workflow to export high-quality training data"

---

### Pattern 3: Workflow Execution

**User Intent**: Execute a designed workflow

```
User: execute workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890

Skill: ✅ Workflow executed successfully!

       ⏱️ Execution time: 1250ms
       📊 Records processed: 847
       ✨ Quality score: 94.3%

       📈 Results:
         1. {"product": "Widget A", "sentiment": 0.85, "category": "electronics"}...
         2. {"product": "Widget B", "sentiment": 0.92, "category": "electronics"}...
         3. {"product": "Gadget C", "sentiment": 0.78, "category": "home"}...

       💡 To compare with raw data: "compare workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**Variations**:
- "run workflow customer-sentiment"
- "execute the sentiment analysis workflow"

---

### Pattern 4: Quality Comparison

**User Intent**: Compare governed vs raw data quality

```
User: compare workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890

Skill: 📊 Data Quality Comparison

       🏆 Governed Data:
         • Completeness: 96.5%
         • Accuracy: 94.3%
         • Consistency: 97.8%
         • Overall Quality: 96.2%

       📉 Raw Data:
         • Completeness: 78.2%
         • Accuracy: 71.5%
         • Consistency: 69.3%
         • Overall Quality: 73.0%

       ✨ Improvement:
         • Completeness: +18.3%
         • Accuracy: +22.8%
         • Consistency: +28.5%
         • Overall: +23.2%

       💡 Governed data shows 23% better quality!
```

---

## Natural Language Understanding

### Query Keywords

The skill recognizes these patterns:

**Dataset Selection**:
- "dataset: name" or "from dataset name"
- "in dataset name" or "dataset name"

**Status Filtering**:
- "annotated" → completed status
- "pending" → pending status
- "in progress" → in_progress status

**Quality Filtering**:
- "quality: 0.9" or "quality score 0.9"
- "quality above 0.85" or "min quality 0.9"

**Limiting Results**:
- "top 10" or "first 20"
- "limit 5" or "show 15"

### Workflow Keywords

**Design/Create**:
- "design workflow" or "create workflow"
- "build workflow" or "design a pipeline"

**Execute/Run**:
- "execute workflow" or "run workflow"
- "execute the workflow" or "run pipeline"

**Compare**:
- "compare workflow" or "comparison"
- "compare results" or "show comparison"

---

## Channel-Specific Behavior

### WhatsApp
- **Max message length**: 4096 characters
- **Records per message**: 5
- **Format**: Plain text with emojis
- **Pagination**: Automatic truncation with "..." indicator

### Telegram
- **Max message length**: 2000 characters
- **Records per message**: 10
- **Format**: Plain text with emojis
- **Pagination**: Page numbers shown

### Slack
- **Max message length**: 2000 characters
- **Records per message**: 5
- **Format**: Plain text with emojis
- **Pagination**: Page numbers shown

### Discord
- **Max message length**: 2000 characters
- **Records per message**: 5
- **Format**: Plain text with emojis
- **Pagination**: Page numbers shown

---

## Error Handling

### Authentication Errors

**Symptom**: "Unable to connect to SuperInsight"

**Causes**:
- Invalid API key
- Expired credentials
- Network connectivity issues

**User Message**:
```
Unable to connect to SuperInsight. Please check your API credentials.
```

**Resolution**:
1. Verify `SUPERINSIGHT_API_KEY` is set correctly
2. Check API key hasn't been revoked
3. Ensure network connectivity to SuperInsight

---

### Permission Errors

**Symptom**: HTTP 403 responses

**Causes**:
- Insufficient permissions for dataset
- Tenant isolation violation
- Revoked access

**User Message**:
```
You do not have permission to access this data. Please contact your administrator.
```

**Resolution**:
1. Verify user has access to requested dataset
2. Check tenant assignment is correct
3. Contact administrator to grant permissions

---

### Rate Limiting

**Symptom**: HTTP 429 responses

**Causes**:
- Too many requests in time window
- Quota exceeded

**User Message**:
```
Rate limit exceeded. Please try again in 60 seconds.
```

**Resolution**:
1. Wait for the specified retry period
2. Reduce query frequency
3. Contact administrator to increase limits

---

### Workflow Errors

**Symptom**: Workflow execution fails

**Causes**:
- Invalid workflow ID
- Missing data sources
- Processing step errors

**User Message**:
```
Workflow execution failed: [specific error]. Please check your workflow definition.
```

**Resolution**:
1. Verify workflow ID is correct
2. Check data sources are available
3. Review workflow steps for errors
4. Re-design workflow if needed

---

## Troubleshooting Guide

### Issue: Skill not responding

**Symptoms**:
- No response from skill
- Timeout errors

**Diagnosis**:
1. Check OpenClaw agent is running
2. Verify skill is installed in OpenClaw
3. Check SuperInsight API is accessible

**Solution**:
```bash
# Check OpenClaw agent status
docker ps | grep openclaw-agent

# Check skill installation
docker exec openclaw-agent ls /app/skills/

# Test API connectivity
curl http://backend:8000/health
```

---

### Issue: Authentication keeps failing

**Symptoms**:
- Repeated "Unable to connect" messages
- 401 errors in logs

**Diagnosis**:
1. Check API key is valid
2. Verify environment variables are set
3. Check token expiry handling

**Solution**:
```bash
# Verify environment variables
docker exec openclaw-agent env | grep SUPERINSIGHT

# Test authentication manually
curl -X POST http://backend:8000/api/v1/ai-integration/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'
```

---

### Issue: Workflow design fails

**Symptoms**:
- "Failed to parse workflow" errors
- Incomplete workflow definitions

**Diagnosis**:
1. Check workflow description is clear
2. Verify data sources exist
3. Review processing steps

**Solution**:
- Use more specific language in workflow description
- Break complex workflows into smaller steps
- Verify dataset names are correct
- Example: "Design a workflow to filter customer_reviews by quality > 0.9 and export as JSON"

---

### Issue: Quality comparison shows no improvement

**Symptoms**:
- Comparison shows 0% improvement
- Governed and raw data metrics are identical

**Diagnosis**:
1. Check if data governance is enabled
2. Verify quality evaluation is running
3. Review data processing pipeline

**Solution**:
1. Ensure data has been through governance pipeline
2. Check quality scores are calculated
3. Verify comparison is using correct data sources

---

## Performance Tips

### Optimize Queries

**Use specific filters**:
```
❌ "Show me all data"
✅ "Show me data from dataset reviews with quality > 0.9"
```

**Limit result size**:
```
❌ "Get all annotated records"
✅ "Get top 10 annotated records"
```

### Optimize Workflows

**Break into smaller steps**:
```
❌ "Design a workflow to do everything with all data"
✅ "Design a workflow to filter reviews by quality, then analyze sentiment"
```

**Use appropriate data sources**:
```
❌ "Use all datasets"
✅ "Use dataset customer_reviews"
```

---

## Advanced Usage

### Chaining Workflows

Design workflows that build on each other:

```
User: Design a workflow to extract high-quality reviews
Skill: [Creates workflow A]

User: Design a workflow to analyze sentiment from workflow A results
Skill: [Creates workflow B that uses A's output]
```

### Batch Processing

Process multiple datasets:

```
User: Design a workflow to process datasets reviews, feedback, and comments
Skill: [Creates workflow with multiple data sources]
```

### Custom Formatting

Request specific output formats:

```
User: Design a workflow to export as CSV with columns: id, text, sentiment
Skill: [Creates workflow with custom output format]
```

---

## API Integration Details

### Authentication Flow

1. Skill sends API key to `/api/v1/ai-integration/auth/token`
2. Receives JWT token (valid 1 hour)
3. Caches token in memory
4. Refreshes 5 minutes before expiry
5. Automatically retries on 401 errors

### Workflow API Calls

**Parse workflow**:
```
POST /api/v1/ai-integration/workflows/parse
Body: { "description": "natural language description" }
Response: { "id": "uuid", "name": "...", "steps": [...] }
```

**Execute workflow**:
```
POST /api/v1/ai-integration/workflows/{id}/execute
Body: { "use_governed_data": true }
Response: { "results": [...], "quality_score": 0.95, ... }
```

**Compare results**:
```
POST /api/v1/ai-integration/workflows/{id}/compare
Response: { "governed_data": {...}, "raw_data": {...}, "improvement": {...} }
```

---

## Security Considerations

### Data Access
- All queries filtered by tenant
- API key tied to single tenant
- Cross-tenant access blocked

### Token Management
- Tokens cached in memory only
- Automatic refresh before expiry
- No token persistence to disk

### Audit Logging
- All queries logged with user/channel
- Workflow executions tracked
- Comparison requests audited

---

## Version History

### v2.0.0 (2026-02-04)
- ✅ Added workflow design capabilities
- ✅ Added workflow execution
- ✅ Added quality comparison
- ✅ Enhanced error handling for workflows
- ✅ Added conversation patterns documentation

### v1.0.0 (2026-01-15)
- ✅ Initial release
- ✅ Data querying with natural language
- ✅ Channel-appropriate formatting
- ✅ Authentication and authorization
- ✅ Error handling

---

## Support

**Documentation**: See README.md for installation and configuration

**Issues**: Report bugs and feature requests to the SuperInsight team

**Examples**: See conversation patterns above for usage examples

**API Reference**: https://docs.superinsight.ai/ai-integration
