podman-build:
	podman build -t ai-foundry-backend .

podman-run:
	podman run --rm -it -p 8080:8080 \
	--name ai-foundry-backend --network=ai-foundry \
	-e OPENAI_API_KEY \
	--env-file .env.local ai-foundry-backend:latest