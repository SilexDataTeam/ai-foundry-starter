podman-build:
	podman build -t ai-foundry-chat-app .

podman-run:
	podman run --rm -it -p 3000:3000 --name ai-foundry-chat-app \
	--network=ai-foundry \
	-v ./.env.local:/workspace/chat-app/.env.local ai-foundry-chat-app:latest