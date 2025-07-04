from typing import Any

import aiohttp
import pytest
from pytest_mock import MockerFixture
from yarl import URL

from aiohttp_aws_auth import AwsCredentials, AwsSigV4Auth

from .conftest import assert_headers


@pytest.mark.freeze_time("2024-03-14T12:08:40+0000")
@pytest.mark.parametrize("method_name", ["GET", "GeT", "get"], ids=["GET", "GeT", "get"])
async def test_aws_request_auth_simple_get(method_name: str, mocker: MockerFixture) -> None:
    # Arrange
    credentials = AwsCredentials(
        access_key="access_key",
        secret_key="secret_key",
        session_token="session_token",
    )

    auth = AwsSigV4Auth(credentials=credentials, region="eu-west-1")
    request = aiohttp.ClientRequest(
        method=method_name,
        url=URL("https://api.example.com"),
    )

    # Act
    headers_received = {}

    async def handler(request: aiohttp.ClientRequest) -> aiohttp.ClientResponse:
        headers_received.update(dict(request.headers))
        return mocker.Mock()

    await auth(request, handler)

    # Assert
    assert_headers(
        headers_received,
        {
            "host": "api.example.com",
            "authorization": "AWS4-HMAC-SHA256 "
            + "Credential=access_key/20240314/eu-west-1/execute-api/aws4_request, "
            + "SignedHeaders=host;x-amz-date;x-amz-security-token, "
            + "Signature=deae23bb2dca27aa37770a33d62af0d9ac0443cb61dcca3fea2682974752e78d",
            "x-amz-date": "20240314T120840Z",
            "x-amz-content-sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "x-amz-security-token": "session_token",
        },
    )


@pytest.mark.freeze_time("2024-03-14T12:08:40+0000")
@pytest.mark.parametrize(
    "query_params, query_params_string",
    [
        ({"param1": "some value", "param2": "a diff value"}, ""),
        ({"param2": "a diff value", "param1": "some value"}, ""),
        (None, "param1=some+value&param2=a+diff+value"),
        (None, "param2=a+diff+value&param1=some+value"),
    ],
    ids=["dict_sort", "dict_sort_reverse", "string_sort", "string_sort_reverse"],
)
async def test_aws_request_auth_get_query_strings(
    query_params: Any, query_params_string: str, mocker: MockerFixture
) -> None:
    # Arrange
    credentials = AwsCredentials(
        access_key="access_key",
        secret_key="secret_key",
        session_token="session_token",
    )

    url = "https://api.example.com"
    if query_params_string:
        url += "?" + query_params_string

    auth = AwsSigV4Auth(credentials=credentials, region="eu-west-1")
    request = aiohttp.ClientRequest(
        method="GET",
        url=URL(url),
        params=query_params,
    )

    # Act
    headers_received = {}

    async def handler(request: aiohttp.ClientRequest) -> aiohttp.ClientResponse:
        headers_received.update(dict(request.headers))
        return mocker.Mock()

    await auth(request, handler)

    # Assert
    assert_headers(
        headers_received,
        {
            "host": "api.example.com",
            "authorization": "AWS4-HMAC-SHA256 "
            + "Credential=access_key/20240314/eu-west-1/execute-api/aws4_request, "
            + "SignedHeaders=host;x-amz-date;x-amz-security-token, "
            + "Signature=ad22e5c46b0d5927747edd33245c7eee70322c63c789a9f5285c9339c46c8784",
            "x-amz-date": "20240314T120840Z",
            "x-amz-content-sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "x-amz-security-token": "session_token",
        },
    )


@pytest.mark.freeze_time("2024-03-14T12:08:40+0000")
async def test_aws_request_auth_post_content(mocker: MockerFixture) -> None:
    # Arrange
    credentials = AwsCredentials(
        access_key="access_key",
        secret_key="secret_key",
        session_token="session_token",
    )

    auth = AwsSigV4Auth(credentials=credentials, region="eu-west-1")
    request = aiohttp.ClientRequest(
        method="POST",
        url=URL("https://api.example.com"),
        data={"key1": "value1", "key2": "value2"},
    )

    # Act
    headers_received = {}

    async def handler(request: aiohttp.ClientRequest) -> aiohttp.ClientResponse:
        headers_received.update(dict(request.headers))
        return mocker.Mock()

    await auth(request, handler)

    # Assert
    assert_headers(
        headers_received,
        {
            "host": "api.example.com",
            "content-length": "33",
            "content-type": "application/json",
            "authorization": "AWS4-HMAC-SHA256 "
            + "Credential=access_key/20240314/eu-west-1/execute-api/aws4_request, "
            + "SignedHeaders=host;x-amz-date;x-amz-security-token, "
            + "Signature=f1808546ef192f3141bb08a678fed95b623f1611c11dbe5d67323a0a04aa6e13",
            "x-amz-date": "20240314T120840Z",
            "x-amz-content-sha256": "b734413c644ec49f6a7c07d88b267244582d6422d89eee955511f6b3c0dcb0f2",
            "x-amz-security-token": "session_token",
        },
    )
