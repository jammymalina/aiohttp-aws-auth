import asyncio
import hashlib
import hmac
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import aiohttp


@dataclass
class AwsCredentials:
    access_key: str
    secret_key: str
    session_token: str | None = None
    expiration: datetime = field(default_factory=lambda: datetime.max.replace(tzinfo=timezone.utc))

    def is_expired(self) -> bool:
        current_time = datetime.now(timezone.utc)
        return current_time >= self.expiration

    @classmethod
    def from_assume_role_credentials(cls, credentials: dict, refresh_buffer: timedelta) -> "AwsCredentials":
        access_key = credentials["AccessKeyId"]
        secret_key = credentials["SecretAccessKey"]
        session_token = credentials.get("SessionToken")

        expiration: datetime = credentials.get("Expiration", datetime.max.replace(tzinfo=timezone.utc))

        if not expiration.tzinfo:
            expiration = expiration.replace(tzinfo=timezone.utc)

        return cls(
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            expiration=expiration.astimezone(timezone.utc) - refresh_buffer,
        )


class AwsSigV4AuthSigner:
    def __init__(self, service: str, region: str) -> None:
        self._service = service
        self._region = region

    async def get_aws_auth_headers(self, request: aiohttp.ClientRequest, credentials: AwsCredentials) -> dict[str, str]:
        current_time = datetime.now(timezone.utc)
        amzdate = current_time.strftime("%Y%m%dT%H%M%SZ")
        datestamp = current_time.strftime("%Y%m%d")

        aws_host = request.url.raw_authority

        canonical_uri = self._get_canonical_path(request)
        canonical_querystring = self._get_canonical_querystring(request)

        canonical_headers = "host:" + aws_host + "\n" + "x-amz-date:" + amzdate + "\n"
        if credentials.session_token:
            canonical_headers += "x-amz-security-token:" + credentials.session_token + "\n"

        signed_headers = "host;x-amz-date"
        if credentials.session_token:
            signed_headers += ";x-amz-security-token"

        if isinstance(request.body, bytes):
            payload_bytes = request.body
        else:
            payload_bytes = await request.body.as_bytes()
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        canonical_request: str = (
            str(request.method)
            + "\n"
            + canonical_uri
            + "\n"
            + canonical_querystring
            + "\n"
            + canonical_headers
            + "\n"
            + signed_headers
            + "\n"
            + payload_hash
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = datestamp + "/" + self._region + "/" + self._service + "/" + "aws4_request"
        string_to_sign = (
            algorithm
            + "\n"
            + amzdate
            + "\n"
            + credential_scope
            + "\n"
            + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        )

        signing_key = self._get_signature_key(
            secret_key=credentials.secret_key,
            datestamp=datestamp,
            region=self._region,
        )

        string_to_sign_utf8 = string_to_sign.encode("utf-8")
        signature = hmac.new(signing_key, string_to_sign_utf8, hashlib.sha256).hexdigest()

        authorization_header = (
            algorithm
            + " "
            + "Credential="
            + credentials.access_key
            + "/"
            + credential_scope
            + ", "
            + "SignedHeaders="
            + signed_headers
            + ", "
            + "Signature="
            + signature
        )

        headers = {
            "Authorization": authorization_header,
            "x-amz-date": amzdate,
            "x-amz-content-sha256": payload_hash,
        }
        if credentials.session_token:
            headers["X-Amz-Security-Token"] = credentials.session_token
        return headers

    def __sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, secret_key: str, datestamp: str, region: str) -> bytes:
        signed_date = self.__sign(("AWS4" + secret_key).encode("utf-8"), datestamp)
        signed_region = self.__sign(signed_date, region)
        signed_service = self.__sign(signed_region, self._service)
        signature = self.__sign(signed_service, "aws4_request")
        return signature

    def _get_canonical_path(self, request: aiohttp.ClientRequest) -> str:
        return quote(request.url.path if request.url.path else "/", safe="/-_.~")

    def _get_canonical_querystring(self, request: aiohttp.ClientRequest) -> str:
        canonical_querystring = ""

        querystring_sorted = "&".join(sorted(request.url.query_string.split("&")))

        for query_param in querystring_sorted.split("&"):
            key_val_split = query_param.split("=", 1)

            key = key_val_split[0]
            if len(key_val_split) > 1:
                val = key_val_split[1]
            else:
                val = ""

            if key:
                if canonical_querystring:
                    canonical_querystring += "&"
                canonical_querystring += "=".join([key, val])

        return canonical_querystring


class AwsSigV4Auth:
    def __init__(self, credentials: AwsCredentials, region: str, service: str = "execute-api") -> None:
        self._credentials = credentials
        self._signer = AwsSigV4AuthSigner(service=service, region=region)

    async def __call__(self, req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType) -> aiohttp.ClientResponse:
        aws_headers = await self._signer.get_aws_auth_headers(request=req, credentials=self._credentials)
        req.headers.update(aws_headers)
        return await handler(req)


class AwsSigV4AssumeRoleAuth:
    def __init__(
        self,
        region: str,
        role_arn: str,
        service: str = "execute-api",
        session: Any = None,
        async_session: Any = None,
        client_kwargs: dict | None = None,
        async_client_kwargs: dict | None = None,
        duration: timedelta | None = None,
        refresh_buffer: timedelta | None = None,
    ) -> None:
        self._role_arn = role_arn
        self._session = session
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        self._async_session = async_session
        self._client_kwargs = client_kwargs or {}
        self._async_client_kwargs = async_client_kwargs or {}
        self._credentials: AwsCredentials | None = None
        self._async_credentials: AwsCredentials | None = None
        self._duration = duration or timedelta(seconds=3600)
        self._refresh_buffer = refresh_buffer or timedelta(seconds=0)
        self._signer = AwsSigV4AuthSigner(service=service, region=region)

    async def get_async_credentials(self) -> None:
        async with self._async_lock:
            if self._async_credentials and not self._async_credentials.is_expired():
                return

            async with self._async_session.client("sts", **self._async_client_kwargs) as sts:
                response = await sts.assume_role(
                    RoleArn=self._role_arn,
                    RoleSessionName=str(uuid.uuid4()),
                    DurationSeconds=int(self._duration.total_seconds()),
                )

                self._async_credentials = AwsCredentials.from_assume_role_credentials(
                    response["Credentials"],
                    refresh_buffer=self._refresh_buffer,
                )

    async def __call__(self, req: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType) -> aiohttp.ClientResponse:
        if self._async_session is None:
            raise ValueError("Please specify the async session")

        await self.get_async_credentials()
        aws_headers = await self._signer.get_aws_auth_headers(request=req, credentials=self._async_credentials)  # type: ignore
        req.headers.update(aws_headers)
        return await handler(req)
