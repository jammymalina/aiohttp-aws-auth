# aiohttp-aws-auth

## Overview

This module provides AWS Signature Version 4 (SigV4) authentication for aiohttp. It includes two main classes:

- `AwsSigV4Auth`: For direct AWS credential authentication
- `AwsSigV4AssumeRoleAuth`: For authentication using AWS IAM Role assumption

## Features

- Simple integration with HTTPX
- Support for both synchronous and asynchronous authentication
- AWS SigV4 signing for API requests
- IAM Role assumption with configurable duration
- Credential expiration and automatic refresh
- Flexible configuration options

## Installation

Install the package using pip:

```bash
pip install httpx-aws-auth
```

## Usage

### Basic AWS Credentials Authentication

```python
import httpx
from httpx_aws_auth import AwsSigV4Auth, AwsCredentials

# Create AWS credentials
credentials = AwsCredentials(
    access_key='YOUR_ACCESS_KEY',
    secret_key='YOUR_SECRET_KEY'
)

# Create an authenticated client
client = httpx.Client(
    auth=AwsSigV4Auth(
        credentials=credentials,
        region='us-west-2',
        service='execute-api'
    )
)

# Make a request
response = client.get('https://your-api-endpoint.com')
```

### IAM Role Assumption (Synchronous)

```python
import boto3
from httpx_aws_auth import AwsSigV4AssumeRoleAuth

# Create AWS session
session = boto3.Session()

# Create an authenticated client with role assumption
client = httpx.Client(
    auth=AwsSigV4AssumeRoleAuth(
        region='us-west-2',
        role_arn='arn:aws:iam::123456789012:role/YourRole',
        session=session,
        duration=timedelta(hours=1)
    )
)

# Make a request
response = client.get('https://your-api-endpoint.com')
```

### IAM Role Assumption (Asynchronous)

```python
import aioboto3
from httpx_aws_auth import AwsSigV4AssumeRoleAuth

# Create async AWS session
async_session = aioboto3.Session()

# Create an authenticated async client with role assumption
async_client = httpx.AsyncClient(
    auth=AwsSigV4AssumeRoleAuth(
        region='us-west-2',
        role_arn='arn:aws:iam::123456789012:role/YourRole',
        async_session=async_session,
        duration=timedelta(hours=1)
    )
)

# Make an async request
async with async_client as client:
    response = await client.get('https://your-api-endpoint.com')
```

## Configuration Options

### AwsSigV4Auth

- `credentials`: AWS credentials object
- `region`: AWS region
- `service`: AWS service name (default: 'execute-api')

### AwsSigV4AssumeRoleAuth

- `region`: AWS region
- `role_arn`: IAM Role ARN to assume
- `service`: AWS service name (default: 'execute-api')
- `session`: Synchronous boto3 session
- `async_session`: Asynchronous aioboto3 session
- `duration`: Credential validity duration (default: 1 hour)
- `refresh_buffer`: Time before expiration to refresh credentials (default: 0 seconds)

## Dependencies

- aiohttp
- boto3 (for synchronous authentication)
- aioboto3 (for asynchronous authentication)
