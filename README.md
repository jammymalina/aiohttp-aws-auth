# aiohttp-aws-auth

## Overview

This module provides AWS Signature Version 4 (SigV4) authentication for aiohttp through two primary middleware classes:

- `AwsSigV4Auth`: For direct AWS credential authentication
- `AwsSigV4AssumeRoleAuth`: For authentication using AWS IAM Role assumption

## Features

- Simple integration with aiohttp
- Support for both synchronous and asynchronous authentication
- AWS SigV4 signing for API requests
- IAM Role assumption with configurable duration
- Credential expiration and automatic refresh
- Flexible configuration options

## Installation

Install the package using pip:

```bash
pip install aiohttp-aws-auth
```

## Usage

### Basic AWS Credentials Authentication

```python
import aiohttp
from aiohttp_aws_auth import AwsSigV4Auth, AwsCredentials

# Create AWS credentials
credentials = AwsCredentials(
    access_key='YOUR_ACCESS_KEY',
    secret_key='YOUR_SECRET_KEY'
)

# Create an authentication middleware
aws_auth_middleware = AwsSigV4Auth(
    credentials=credentials,
    region='us-west-2',
    service='execute-api',
)


# Make a request
async with ClientSession(middlewares=(aws_auth_middleware,)) as session:
    resp = await session.get("https://your-api-endpoint.com")
```

### IAM Role Assumption

```python
import aioboto3
from aiohttp_aws_auth import AwsSigV4AssumeRoleAuth

# Create async AWS session
session = aioboto3.Session()

# Create an authentication middleware
aws_auth_middleware = AwsSigV4AssumeRoleAuth(
    region='us-west-2',
    role_arn='arn:aws:iam::123456789012:role/YourRole',
    session=session,
    duration=timedelta(hours=1),
)

# Make an async request
async with ClientSession(middlewares=(aws_auth_middleware,)) as session:
    resp = await session.get("https://your-api-endpoint.com")
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
- aioboto3 (only needed when using AwsSigV4AssumeRoleAuth)
