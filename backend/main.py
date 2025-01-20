# Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import time
from typing import Any, Optional, TypedDict

import jwt
import requests
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from .routes.chat_title import router as chat_title_router
from .routes.events import router as events_router
from .routes.feedback import router as feedback_router
from .telemetry import setup_telemetry

# DISABLE_AUTH can be utilized to disable authentication for testing purposes
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"

# DISABLE_TELEMETRY can be utilized to disable telemetry for testing purposes
DISABLE_TELEMETRY = os.getenv("DISABLE_TELEMETRY", "false").lower() == "true"

# DISABLE_TLS_VERIFY can be utilized to disable TLS verification for testing purposes
DISABLE_TLS_VERIFY = os.getenv("DISABLE_TLS_VERIFY", "false").lower() == "true"

# Warn if TLS verification is disabled
if DISABLE_TLS_VERIFY:
    logging.warning("TLS verification is disabled")

# Configure root logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Print entire environment variables
logger.info("Environment variables:")
for key, value in os.environ.items():
    logger.info(f"  {key}: {value}")

# OAuth2 configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
ISSUER_URL = os.getenv("ISSUER_URL", KEYCLOAK_URL)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "myrealm")
FRONTEND_KEYCLOAK_CLIENT_ID = os.getenv(
    "FRONTEND_KEYCLOAK_CLIENT_ID", "ai-foundry-chat-app"
)

# CORS configuration (comma-separated)
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(
    ","
)

# Print environment setup
logger.info("Environment setup:")
logger.info(f"  DISABLE_AUTH: {DISABLE_AUTH}")
logger.info(f"  DISABLE_TELEMETRY: {DISABLE_TELEMETRY}")
logger.info(f"  KEYCLOAK_URL: {KEYCLOAK_URL}")
logger.info(f"  ISSUER_URL: {ISSUER_URL}")
logger.info(f"  KEYCLOAK_REALM: {KEYCLOAK_REALM}")
logger.info(f"  FRONTEND_KEYCLOAK_CLIENT_ID: {FRONTEND_KEYCLOAK_CLIENT_ID}")
logger.info(f"  CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")

# Initialize FastAPI security
if not DISABLE_AUTH:
    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl=f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    )

    # Define type for public key cache

    class PublicKeyCache(TypedDict):
        key: Optional[str]
        timestamp: float
        ttl: int

    # Cache for public key to avoid repeated requests
    _public_key_cache: PublicKeyCache = {
        "key": None,
        "timestamp": 0.0,
        "ttl": 300,  # 5 minutes cache
    }

    def get_public_key() -> str:
        current_time = time.time()
        if (
            _public_key_cache["key"] is not None
            and current_time - _public_key_cache["timestamp"] < _public_key_cache["ttl"]
        ):
            logger.debug("Using cached public key")
            return _public_key_cache["key"]

        try:
            url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
            logger.debug(f"Fetching public key from {url}")
            response = requests.get(url, verify=not DISABLE_TLS_VERIFY)
            response.raise_for_status()
            key = response.json()["public_key"]
            public_key = f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"

            _public_key_cache.update(
                {
                    "key": public_key,
                    "timestamp": current_time,
                    "ttl": _public_key_cache["ttl"],
                }
            )
            logger.info("Successfully retrieved new public key")
            return public_key

        except Exception as e:
            logger.error(f"Failed to fetch public key: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch public key: {str(e)}"
            )

    async def verify_token(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
        try:
            # First decode without verification to inspect claims
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.debug("Token claims:")
            logger.debug(f"  aud: {unverified.get('aud')}")
            logger.debug(f"  azp: {unverified.get('azp')}")
            logger.debug(f"  iss: {unverified.get('iss')}")
            logger.debug(f"  sub: {unverified.get('sub')}")

            public_key = get_public_key()
            logger.debug("Verifying token with public key")

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="account",
                issuer=f"{ISSUER_URL}/realms/{KEYCLOAK_REALM}",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            if not isinstance(payload, dict):
                logger.error(f"Invalid payload: {payload}")
                raise HTTPException(status_code=401, detail="Invalid token")

            if payload.get("azp") != FRONTEND_KEYCLOAK_CLIENT_ID:
                logger.error(f"Invalid azp: {payload.get('azp')}")
                raise HTTPException(status_code=401, detail="Invalid token")

            logger.info(
                f"Successfully verified token for user: {payload.get('preferred_username')}"
            )
            return payload

        except ExpiredSignatureError:
            logger.error("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed",
                headers={"WWW-Authenticate": "Bearer"},
            )


app = FastAPI(
    title="AI Foundry Sandbox",
    description="Sandbox for AI Foundry services.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Authorization", "Content-Type"],
)

# Initialize telemetry
if not DISABLE_TELEMETRY:
    setup_telemetry(service_name="AI Foundry Sandbox")

# Include route modules with or without authentication
routes = [events_router, feedback_router, chat_title_router]
for route in routes:
    if not DISABLE_AUTH:
        app.include_router(route, dependencies=[Depends(verify_token)])
    else:
        app.include_router(route)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
