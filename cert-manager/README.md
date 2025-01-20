**Steps to setup cert-manager**

1. These steps assume that the Let's Encrypt certificate issuer & Cloudflare for DNS-01 verification will be utilized. You may customize the setup for your own environment. Please reference the `cert-manager` documentation for the supported issues and verification methods.
2.  Install `cert-manager` operator:
    ```
    kubectl apply -f k8s/100-install-cert-manager-operator.yaml
    ```
3. Create the secret for DNS-01 verification (assumes Cloudflare and an API token has been generated already):
    ```
    CLOUDFLARE_API_TOKEN=$(echo -n "<Cloudflare API token> | base64 -i -) envsubst < k8s/200-create-dns-secret.yaml | kubectl apply -f -
    ```
4. Create the `ClusterIssuer`:
    ```
    ACME_EMAIL_ADDRESS=<email address for certificate generation> CLOUDFLARE_EMAIL_ADDRESS=<Cloudflare account email> envsubst < k8s/300-create-clusterissuer.yaml | kubectl apply -f -
    ```