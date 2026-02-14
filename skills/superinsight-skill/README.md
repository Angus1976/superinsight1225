# SuperInsight Skill for OpenClaw

A custom OpenClaw skill that enables querying and analyzing SuperInsight governed data through conversational interfaces across multiple channels (WhatsApp, Telegram, Slack, Discord, etc.).

## Features

- **Authentication**: Secure authentication with SuperInsight API using API keys and JWT tokens
- **Natural Language Query Parsing**: Translates conversational queries into API calls
- **Data Access**: Queries governed data with filtering, pagination, and quality metrics
- **Channel-Appropriate Formatting**: Formats results for different messaging platforms
- **User-Friendly Error Handling**: Provides clear error messages with corrective actions

## Requirements

- Node.js >= 18.0.0
- SuperInsight platform with AI Integration enabled
- Valid API credentials

## Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your SuperInsight API credentials
```

3. Deploy to OpenClaw:
```bash
# Copy skill to OpenClaw skills directory
cp -r . /path/to/openclaw/skills/superinsight-skill/
```

## Configuration

### Environment Variables

- `SUPERINSIGHT_API_URL`: SuperInsight API base URL (default: `http://backend:8000`)
- `SUPERINSIGHT_API_KEY`: API key for authentication (required)
- `SUPERINSIGHT_TENANT_ID`: Tenant ID for multi-tenant isolation (required)
- `SKILL_TIMEOUT`: Request timeout in milliseconds (default: `30000`)

## Usage

### Basic Query

```
User: Show me annotated data from dataset customer_reviews
Skill: Found 150 records (page 1):
       • ID: abc123 | Status: completed | Quality: 95.2%
       • ID: def456 | Status: completed | Quality: 92.8%
       ...
```

### Quality Filtering

```
User: Get data with quality score above 0.9
Skill: Found 45 records (page 1):
       • ID: xyz789 | Status: completed | Quality: 94.5%
       ...
```

### Pagination

```
User: Show me the first 10 records
Skill: Found 150 records (page 1):
       [10 records displayed]
       Page 1 of 15
```

## Natural Language Query Patterns

The skill understands various query patterns:

- **Dataset filtering**: "dataset: customer_reviews" or "from dataset customer_reviews"
- **Annotation status**: "annotated data" or "pending annotations"
- **Quality filtering**: "quality: 0.9" or "quality score above 0.9"
- **Limiting results**: "top 10" or "first 20" or "limit 5"

## Channel Support

The skill automatically formats results for different channels:

- **WhatsApp**: Max 4096 characters, 5 records per message
- **Telegram**: Max 2000 characters, 10 records per message
- **Slack**: Max 2000 characters, 5 records per message
- **Discord**: Max 2000 characters, 5 records per message

## Error Handling

The skill provides user-friendly error messages:

- **Authentication errors**: "Unable to connect to SuperInsight. Please check your API credentials."
- **Permission errors**: "You do not have permission to access this data. Please contact your administrator."
- **Network errors**: "Cannot reach SuperInsight service. Please try again later."
- **Rate limiting**: "Rate limit exceeded. Please try again in 60 seconds."

## API Integration

The skill integrates with SuperInsight's AI Integration APIs:

- `POST /api/v1/ai-integration/auth/token` - Authentication
- `GET /api/v1/ai-integration/data/query` - Data query
- `POST /api/v1/ai-integration/data/export-for-skill` - Data export
- `GET /api/v1/ai-integration/data/quality-metrics` - Quality metrics

## Development

### Running Tests

```bash
npm test
```

### Linting

```bash
npm run lint
```

### Testing Locally

```javascript
const skill = require('./index');

// Test query
skill.handle('Show me annotated data', { channel: 'whatsapp' })
  .then(response => console.log(response))
  .catch(error => console.error(error));
```

## Architecture

### Authentication Flow

1. Skill authenticates with API key
2. Receives JWT token (valid for 1 hour)
3. Caches token and refreshes 5 minutes before expiry
4. Automatically retries on 401 errors

### Query Processing Flow

1. Parse natural language query into filters
2. Authenticate with SuperInsight API
3. Query data with tenant filtering
4. Format results for target channel
5. Return formatted message

### Error Handling Flow

1. Catch all errors (network, auth, permission, etc.)
2. Classify error type
3. Generate user-friendly message
4. Suggest corrective actions

## Security

- API keys are stored in environment variables
- JWT tokens are cached in memory (not persisted)
- All requests include tenant filtering
- Automatic token refresh prevents exposure
- No sensitive data in logs

## Multi-Tenant Isolation

The skill enforces strict tenant isolation:

- API key is associated with a single tenant
- All queries automatically filtered by tenant
- Cross-tenant access attempts are rejected
- Audit logs track all data access

## Performance

- Token caching reduces authentication overhead
- Pagination prevents large data transfers
- Configurable timeouts prevent hanging requests
- Channel-specific formatting optimizes message size

## Troubleshooting

### "Unable to connect to SuperInsight"

- Check `SUPERINSIGHT_API_URL` is correct
- Verify network connectivity
- Ensure SuperInsight service is running

### "Authentication failed"

- Verify `SUPERINSIGHT_API_KEY` is valid
- Check API key has not been revoked
- Ensure tenant ID matches API key

### "Rate limit exceeded"

- Wait for the specified retry period
- Contact administrator to increase rate limits
- Optimize queries to reduce request frequency

## License

MIT

## Support

For issues and questions:
- GitHub Issues: [SuperInsight Repository]
- Email: support@superinsight.ai
- Documentation: https://docs.superinsight.ai
