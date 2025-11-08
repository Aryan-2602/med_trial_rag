# AWS Support Case - Exact Text to Copy/Paste

## When filling out the support case, use this exact text:

---

**Subject:**
Lambda Concurrent Executions Limit Increase Request

**Service:**
Lambda

**Limit type:**
Concurrent executions

**Region:**
us-east-2

**Requested limit:**
100 concurrent executions

**Describe your question in detail:**

```
I am requesting an increase in the Lambda concurrent executions limit for my AWS account in the us-east-2 region.

Current limit: 10 concurrent executions
Requested limit: 100 concurrent executions

Use case:
I am deploying a RAG (Retrieval-Augmented Generation) API using AWS Lambda that provides real-time search capabilities over clinical trial data. The Lambda function needs to access the internet (via NAT Gateway) to call the OpenAI API for generating embeddings, and it uses EFS for persistent storage of large FAISS vector indices.

To ensure optimal performance and eliminate cold starts, I need to enable provisioned concurrency for the Lambda function. However, AWS requires maintaining a minimum of 10 unreserved concurrent executions, which means I cannot reserve even 1 execution for provisioned concurrency with my current limit of 10.

Function details:
- Function name: cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ
- Region: us-east-2
- Runtime: Python 3.11
- Memory: 2048 MB
- Architecture: ARM64
- Expected provisioned concurrency: 1 execution

This is a production application handling clinical research queries, and the provisioned concurrency is necessary to:
1. Eliminate cold start delays (which can take 30+ seconds)
2. Ensure consistent response times under the API Gateway 29-second timeout
3. Maintain a warm Lambda container with cached indices in EFS

The requested limit of 100 concurrent executions will provide sufficient headroom for:
- 1 provisioned concurrent execution (for the RAG API)
- Normal on-demand scaling for other Lambda functions
- Future growth and additional functions

This request aligns with AWS best practices for serverless applications requiring consistent performance.

Thank you for your consideration.
```

---

## Alternative shorter version (if character limit):

```
I am requesting an increase in Lambda concurrent executions limit from 10 to 100 in us-east-2 region.

Use case: I need to enable provisioned concurrency (1 execution) for my RAG API Lambda function (cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ) to eliminate cold starts and ensure consistent performance under API Gateway's 29-second timeout. 

AWS requires maintaining a minimum of 10 unreserved concurrent executions, which prevents me from reserving even 1 execution with my current limit of 10. The requested limit of 100 will provide sufficient headroom for provisioned concurrency plus normal scaling for other functions.

This is a production application handling real-time clinical research queries that requires consistent low-latency responses.
```

---

## Quick Copy-Paste Version (No formatting):

Copy this block directly:

```
I am requesting an increase in the Lambda concurrent executions limit for my AWS account in the us-east-2 region.

Current limit: 10 concurrent executions
Requested limit: 100 concurrent executions

Use case:
I am deploying a RAG (Retrieval-Augmented Generation) API using AWS Lambda that provides real-time search capabilities over clinical trial data. The Lambda function needs to access the internet (via NAT Gateway) to call the OpenAI API for generating embeddings, and it uses EFS for persistent storage of large FAISS vector indices.

To ensure optimal performance and eliminate cold starts, I need to enable provisioned concurrency for the Lambda function. However, AWS requires maintaining a minimum of 10 unreserved concurrent executions, which means I cannot reserve even 1 execution for provisioned concurrency with my current limit of 10.

Function details:
- Function name: cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ
- Region: us-east-2
- Runtime: Python 3.11
- Memory: 2048 MB
- Architecture: ARM64
- Expected provisioned concurrency: 1 execution

This is a production application handling clinical research queries, and the provisioned concurrency is necessary to:
1. Eliminate cold start delays (which can take 30+ seconds)
2. Ensure consistent response times under the API Gateway 29-second timeout
3. Maintain a warm Lambda container with cached indices in EFS

The requested limit of 100 concurrent executions will provide sufficient headroom for:
- 1 provisioned concurrent execution (for the RAG API)
- Normal on-demand scaling for other Lambda functions
- Future growth and additional functions

This request aligns with AWS best practices for serverless applications requiring consistent performance.

Thank you for your consideration.
```

