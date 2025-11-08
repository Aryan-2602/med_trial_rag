# Provisioned Concurrency Setup

## Current Issue

AWS Lambda accounts have a minimum unreserved concurrent execution limit. When you try to set provisioned concurrency, it reserves those executions, which cannot reduce your unreserved pool below 10.

**Error:** `Specified ConcurrentExecutions for function decreases account's UnreservedConcurrentExecution below its minimum value of [10]`

## Solutions

### Option 1: Request Concurrency Limit Increase (Recommended)

Increase your account's concurrent execution limit:

```bash
# Check current limits
aws lambda get-account-settings

# Request increase via AWS Support Console or CLI
# Go to: AWS Support > Create Case > Service Limit Increase
# Request: Lambda concurrent executions
# Desired limit: 100 (or more if you have other functions)
```

**Note:** This is usually approved quickly for new accounts.

### Option 2: Use Warm-Up Script (No Cost)

Keep Lambda warm by making periodic requests:

```bash
# Create a simple warm-up script
cat > warmup.sh << 'EOF'
#!/bin/bash
API_URL="https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod"

# Make request every 10 minutes to keep warm
while true; do
  curl -s "$API_URL/health" > /dev/null
  echo "$(date): Lambda warmed up"
  sleep 600  # 10 minutes
done
EOF

chmod +x warmup.sh
# Run in background: nohup ./warmup.sh &
```

### Option 3: Use AWS EventBridge Schedule (Free)

Create a scheduled rule to ping the API every 10 minutes:

```bash
# Create EventBridge rule (runs every 10 minutes)
aws events put-rule \
  --name rag-api-warmup \
  --schedule-expression "rate(10 minutes)" \
  --state ENABLED

# Add Lambda permission
aws lambda add-permission \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --statement-id allow-eventbridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-2:098092129631:rule/rag-api-warmup

# Create target (invoke /health endpoint)
# Note: This requires API Gateway or Lambda direct invocation
```

### Option 4: Accept Cold Starts (No Cost)

- First request after 15+ minutes idle: May timeout (~29s)
- Subsequent requests: Fast (~2-5s)
- Lambda containers stay warm for ~15 minutes

## Current Workaround

Since provisioned concurrency requires account limit increase, you can:

1. **Request limit increase** (takes a few hours/days)
2. **Use warm-up script** (immediate, no cost)
3. **Accept occasional timeouts** (first request after idle)

## After Limit Increase

Once your account limit is increased, enable provisioned concurrency:

```bash
# Create alias if not exists
aws lambda create-alias \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --name live \
  --function-version \$LATEST

# Set provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --qualifier live \
  --provisioned-concurrent-executions 1
```

## Cost Comparison

- **Provisioned Concurrency**: ~$11/month (after limit increase)
- **Warm-up Script**: Free (but requires running machine/instance)
- **EventBridge Schedule**: Free (but needs Lambda direct invocation setup)
- **Accept Cold Starts**: Free

## Recommendation

For immediate use: **Accept cold starts** - subsequent requests work fine.

For production: **Request limit increase** then enable provisioned concurrency.

