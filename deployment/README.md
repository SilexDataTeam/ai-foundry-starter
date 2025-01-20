**Steps to deploy ArgoCD Applications**

1. Install OpenShift GitOps Operator
2. Add `cluster-admin role to service account:
    ```
    oc adm policy add-cluster-role-to-user cluster-admin -z openshift-gitops-argocd-application-controller -n openshift-gitops
    ```
3. Install Helm Chart:
    ```
    helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
    helm install sealed-secrets -n kube-system --set-string fullnameOverride=sealed-secrets-controller sealed-secrets/sealed-secrets
    ```
4. Install `kubeseal` locally:
    ```
    brew install kubeseal
    ```
5. Create SealedSecret using the Konnect-generated `tls.cert` and `tls.key`:
    ```
    kubectl create secret tls kong-cluster-cert -n ai-gateway --cert=tls.crt --key=tls.key -o yaml | kubeseal --controller-name=sealed-secrets-controller --controller-namespace=kube-system --format yaml > kong-cluster-cert-secret.yaml
    ```
6. Deploy `ai-gateway` ArgoCD Application:
    ```
    export CLUSTER_SERVER_NAME=<CLUSTER_SERVER_NAME provided from Konnect>
    export CLUSTER_TELEMETRY_SERVER_NAME=<CLUSTER_TELEMETRY_SERVER_NAME from Konnect>
    envsubst '${CLUSTER_SERVER_NAME} ${CLUSTER_TELEMETRY_SERVER_NAME}' < deployment/ai-gateway-application.yaml | kubectl apply -f -
    ```