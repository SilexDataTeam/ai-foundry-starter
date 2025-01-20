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

from traceloop.sdk import Instruments, Traceloop

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger("telemetry")

# Configure endpoint for the OTLP exporter
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "localhost:4317")
# Configure endpoint security
OTLP_INSECURE = os.getenv("OTLP_INSECURE", "true").lower() == "true"

# Print telemetry environment setup
logger.info("Telemetry environment setup:")
logger.info(f"  OTLP_ENDPOINT: {OTLP_ENDPOINT}")
logger.info(f"  OTLP_INSECURE: {OTLP_INSECURE}")


def setup_telemetry(service_name: str) -> None:
    """
    Configures telemetry (OpenTelemetry + Traceloop) for the FastAPI app.
    """
    # Create an OTLP exporter
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=OTLP_INSECURE)

    try:
        # Initialize Traceloop. This may raise exceptions if the exporter is not available.
        Traceloop.init(
            app_name=service_name,
            disable_batch=False,
            exporter=exporter,
            instruments={Instruments.LANGCHAIN},
        )
        logger.info("Traceloop telemetry initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize Traceloop: %s", exc)
