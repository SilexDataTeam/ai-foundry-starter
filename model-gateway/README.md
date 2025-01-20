**Steps to Install Kong AI Gateway on OpenShift**

*While Red Hat OpenShift is the primary focus of this starter template, most if not all of these steps should work on other k8s distributions than OpenShift.*

**Optional: Install Bitnami Sealed Secrets Helm Chart**

*ArgoCD requires secrets to be managed externally. There are various options per the [ArgoCD Documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/), but the one requirement is that a secret named `kong-cluster-cert`
with the Kong-generated `tls.crt` and `tls.key` must be created.*

1. Install Helm Chart:
    ```
    helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
    ```
2. Install `kubeseal` locally:
    ```
    brew install kubeseal
    ```
3. Create SealedSecret using the Konnect-generated `tls.cert` and `tls.key`:
    ```
    kubectl create secret tls kong-cluster-cert -n ai-gateway --cert=tls.crt --key=tls.key -o yaml | kubeseal --controller-name=sealed-secrets-controller --controller-namespace=kube-system --format yaml > kong-cluster-cert-secret.yaml
    ```

**Required Steps**
1. Register for account on [Kong Connect](https://cloud.konghq.com).
2. Once registered create [Personal Access Token](https://cloud.konghq.com/global/account/tokens) in Konnect. Store the Personal Access Token that you created.
3. Create "New Gateway" in [Gateway Manager](https://cloud.konghq.com/us/gateway-manager/).
4. Choose the "Self-Managed Hybrid" option and enter a Name for the gateway. In the starter we use "ai-gateway" for the gateway name. Click "Next Step".
5. Select "Kubernetes" for Platform. We are using Self-Managed Gateway 3.8 for the Gateway Version.
6. Ensure prerequisites are met as outlined in the setup.
7. Setup Helm:
    1. Create a namespace:
        ```
        kubectl create namespace kong
        ```
    2. Add the Kong charts repository
        ```
        helm repo add kong https://charts.konghq.com
        ```
    3. Update Helm:
        ```
        helm repo update
        ```
8. Click the "Generate certificate" button to generate certificates that will be used as a Kubernetes secret for Helm chart values. Save cluster certificate to `tls.crt` and private key to `tls.key`.
9. Create secret:
```
kubectl create secret tls kong-cluster-cert -n ai-gateway --cert=tls.crt --key=tls.key
```
10. Extract `cluster_server_name` and `cluster_telemetry_server_name` from "Configuration parameters" section, use provided `values.yaml.template`, and install Helm chart.
```
CLUSTER_SERVER_NAME=<cluster_server_name from Konnect-generated values.yaml> \
CLUSTER_TELEMETRY_SERVER_NAME=<cluster_telemetry_server_name from Konnect-generated values.yaml> \
envsubst < values.yaml.template | helm install ai-gateway kong/kong -n ai-gateway --values -
```
11. After Helm chart is installed, the pods will immediately fail to be created with the following error because of SCCs (Security Context Constraints):
```
Error creating: pods "ai-gateway-kong-65cfcb476c-" is forbidden: unable to validate against any security context constraint: [provider "anyuid": Forbidden: not usable by user or serviceaccount, provider "pipelines-scc": Forbidden: not usable by user or serviceaccount, provider restricted-v2: .initContainers[0].runAsUser: Invalid value: 1000: must be in the ranges: [1000870000, 1000879999], provider restricted-v2: .containers[0].runAsUser: Invalid value: 1000: must be in the ranges: [1000870000, 1000879999], provider "restricted": Forbidden: not usable by user or serviceaccount, provider "nonroot-v2": Forbidden: not usable by user or serviceaccount, provider "nonroot": Forbidden: not usable by user or serviceaccount, provider "hostmount-anyuid": Forbidden: not usable by user or serviceaccount, provider "machine-api-termination-handler": Forbidden: not usable by user or serviceaccount, provider "hostnetwork-v2": Forbidden: not usable by user or serviceaccount, provider "hostnetwork": Forbidden: not usable by user or serviceaccount, provider "hostaccess": Forbidden: not usable by user or serviceaccount, provider "lvms-vgmanager": Forbidden: not usable by user or serviceaccount, provider "node-exporter": Forbidden: not usable by user or serviceaccount, provider "privileged": Forbidden: not usable by user or serviceaccount]
```
12. The error can be fixed by adding the `nonroot-v2 `SCC to the appropriate service account:
```
oc adm policy add-scc-to-user nonroot-v2 -z ai-gateway-kong -n ai-gateway
```
13. Wait for the `ai-gateway` deployment to become available:
```
kubectl wait --for=condition=available deployment/ai-gateway-kong -n ai-gateway
```
14. In Konnect verify that the Data Plane Node has been found and click "Done".
15. To deploy our config.yaml with the AI Gateway plugin configuration:
    1. Using the Personal Access Token that was created earlier use the Kong `deck` client to load our `config.yaml`:
        ```
        deck gateway sync config.yaml \
        --konnect-control-plane-name="ai-gateway" \
        --konnect-token=<Personal Access Token>
        ```
    2. From the output of the config sync, verify that the Kong services, routes, and plugins were created. The output should be:
        ```
        creating service ollama_service
        creating service openai_service
        creating route openai_route
        creating route ollama_route
        creating plugin ai-proxy for service ollama_service
        creating plugin ai-proxy for service openai_service
        Summary:
          Created: 6
          Updated: 0
          Deleted: 0
        ```
16. Use the provided `model_vision_test.py` script to test the functionality of the model gateway:
    1. Port forward the Kong proxy port (needs to run in another terminal window):
        ```
        kubectl port-forward -n ai-gateway svc/ai-gateway-kong-proxy 8000:80
        ```
    2. Run the `model_vision_test.py` from the `model-gateway/test` directory (requires the OpenAI Python library to be installed and an OpenAI API key:
        ```
        OPENAI_API_KEY=<OpenAI API key> python model_vision_test.py
        ```
        Output:
        ```
        ChatCompletion(id='chatcmpl-AXd0SqmiHBI2yQ5G8Q4Nyw2RlVEap', choices=[Choice(finish_reason='stop', index=0, logprobs=None, message=ChatCompletionMessage(content='The image shows two cats lying on a pink couch. One cat is sleeping on its back, while the other is curled up beside it. There are also several remote controls placed on the couch between the two cats.', refusal=None, role='assistant', audio=None, function_call=None, tool_calls=None))], created=1732578128, model='gpt-4o-mini-2024-07-18', object='chat.completion', service_tier=None, system_fingerprint='fp_3de1288069', usage=CompletionUsage(completion_tokens=43, prompt_tokens=14180, total_tokens=14223, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=0, audio_tokens=0, reasoning_tokens=0, rejected_prediction_tokens=0), prompt_tokens_details=PromptTokensDetails(audio_tokens=0, cached_tokens=0)))
        ChatCompletion(id='chatcmpl-780', choices=[Choice(finish_reason='stop', index=0, logprobs=None, message=ChatCompletionMessage(content='The image shows two cats lying on a couch, with remotes placed next to them. The cat on the left is smaller and has a long, fluffy tail. It appears to be sleeping or resting, with its head turned towards the right side of the image. The cat on the right is larger and has a shorter, more compact body. It also seems to be asleep or relaxed, with its head facing downwards.\n\nBoth cats are lying on a pink blanket that covers the couch, which is red in color. There are two remotes placed next to them, one on either side of the image. The remotes are white and have various buttons on them, but their exact functions are not clear from the image.\n\nOverall, the image suggests that the cats are enjoying some downtime on the couch, possibly watching TV or taking a nap.', refusal=None, role='assistant', audio=None, function_call=None, tool_calls=None))], created=1732578154, model='llama3.2-vision', object='chat.completion', service_tier=None, system_fingerprint='fp_ollama', usage=CompletionUsage(completion_tokens=169, prompt_tokens=18, total_tokens=187, completion_tokens_details=None, prompt_tokens_details=None))
        ```