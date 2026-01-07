**Steps to Install Keycloak on OpenShift**

1. Go through steps covered in `/vector-database/README.md` to install CNPG. Keycloak requires a trusted certificate, so ensure that
there is a way for the cluster to issue trusted certificates. The AI Foundry Starter utilizes cert-manager and steps can be found to set it up for the Let's Encrypt issuer in `/cert-manager`.
2. Install the Red Hat build of Keycloak Operator:
    ```
    kubectl apply -f k8s/100-install-keycloak-operator.yaml
    ```
3. Create the `keycloak-db`:
    ```
    kubectl apply -f k8s/200-create-database.yaml
    ```
4. Verify status of cluster:
    ```
    kubectl get cluster -n keycloak-operator --watch
    ```
    The output should be:
    ```
    NAME                    AGE   INSTANCES   READY   STATUS                     PRIMARY
    keycloak-db             21m   1           1       Cluster in healthy state   keycloak-db-1
    ```
5. Test connectivity to cluster:
    ```
    kubectl run pg-test-pod --rm -it --image=postgres:latest --restart=Never \
        -n pgvector --env="PGHOST=keycloak-db-rw.keycloak-operator.svc.cluster.local" \
        --env="PGUSER=$(kubectl get secret keycloak-db-superuser -n keycloak-operator -o jsonpath='{.data.username}' | base64 --decode)" \
        --env="PGPASSWORD=$(kubectl get secret keycloak-db-superuser -n keycloak-operator -o jsonpath='{.data.password}' | base64 --decode)" \
        -- sh -c 'exec psql -h $PGHOST -U $PGUSER -c "\conninfo"'
    ```
    The output should be:
    ```
    You are connected to database "postgres" as user "postgres" on host "keycloak-db-rw.keycloak-operator.svc.cluster.local" (address "172.30.173.4") at port "5432".
    SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off, ALPN: none)
    pod "pg-test-pod" deleted
    ```
6. Generate TLS certificate for Keycloak using cert-manager (assumes steps have already been followed in `cert-manager/README.md`):
    ```
    KEYCLOAK_HOSTNAME=<Keycloak hostname> envsubst < k8s/300-create-certificate.yaml | kubectl apply -f 
-
    ```
7. Create Keycloak instance:
    ```
    KEYCLOAK_HOSTNAME=keycloak.dlewis.io envsubst < k8s/400-create-keycloak.yaml | kubectl apply -f -
    ```
8. Verify Keycloak is ready:
    ```
    kubectl get keycloaks/keycloak -o go-template='{{range .status.conditions}}CONDITION: {{.type}}{{"\n"}}  STATUS: {{.status}}{{"\n"}}  MESSAGE: {{.message}}{{"\n"}}{{end}}' -n keycloak-operator
    ```
    The output should be:
    ```
    CONDITION: Ready
        STATUS: True
        MESSAGE: 
    CONDITION: HasErrors
        STATUS: False
        MESSAGE: 
    CONDITION: RollingUpdate
        STATUS: False
        MESSAGE:         
    ```
9. Get initial admin credentials:
    ```
    kubectl get secret keycloak-initial-admin -o jsonpath='{.data.username}' -n keycloak-operator | base64 --decode
    kubectl get secret keycloak-initial-admin -o jsonpath='{.data.password}' -n keycloak-operator | base64 --decode
    ```
10. Create `myrealm` realm, `ai-foundry-chat-app` client, and `test-user` user. For the client:
    - Set `Client authentication` to `Off` (public client for Keycloak.js)
    - Set `Valid Redirect URIs` to `http://<frontend-hostname>/*` (e.g., `http://localhost:3000/*`)
    - Set `Valid post logout redirect URIs` to `http://<frontend-hostname>/*`
    - Set `Web origins` to `http://<frontend-hostname>` (for CORS)