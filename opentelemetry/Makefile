podman-run:
	( \
	  trap 'podman stop otel-collector jaeger' INT; \
	  \
	  echo "Starting OpenTelemetry Collector..."; \
	  podman run -d --rm \
	    --name otel-collector \
	    --network ai-foundry \
	    -p 4317:4317 \
	    -p 4318:4318 \
	    -v ./otel-collector-config.yaml:/otel-collector-config.yaml \
	    opentelemetry-collector:latest \
	    --config=/otel-collector-config.yaml; \
	  \
	  echo "Starting Jaeger..."; \
	  podman run -d --rm \
	    --name jaeger \
	    --network ai-foundry \
	    -p 14250:14250 \
	    -p 14268:14268 \
	    -p 16686:16686 \
	    jaegertracing/all-in-one:latest; \
	  \
	  echo "Both containers are running. Press Ctrl-C to stop..."; \
	  podman logs -f otel-collector & \
	  podman logs -f jaeger & \
	  wait; \
	)