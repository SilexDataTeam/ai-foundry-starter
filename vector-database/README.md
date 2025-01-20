**Steps to Install PGVector on OpenShift**

*While Red Hat OpenShift is the primary focus of this starter template, most if not all of these steps should work on other k8s distributions than OpenShift.*

1. Setup Helm:
    1. Add repository:
        ```
        helm repo add cnpg https://cloudnative-pg.github.io/charts
        ```
    2. Deploy the CloudNativePG operator:
        ```
        helm upgrade --install cnpg \
            --namespace cnpg-system \
            --create-namespace \
            cnpg/cloudnative-pg
        ```
    3. `cnpg-cloudnative-pg` deployment will immediately fail because of SCC permissions. Attach `nonroot-v2` SCC policy to the `cnpg-cloudnative-pg` service account.
        ```
        oc adm policy add-scc-to-user nonroot-v2 -z cnpg-cloudnative-pg -n cnpg-system
        ```
    4. Wait for `cnpg-cloudnative-pg` deployment to become available:
        ```
        kubectl wait --for=condition=available deployment/cnpg-cloudnative-pg -n cnpg-syste,
        ```
    5. Create `pgvector` namespace:
        ```
        kubectl create namespace pgvector
        ```
    6. Create the `ai-foundry-pg-cluster`:
        ```
        kubectl apply -n pgvector -f k8s/100-create-database-cluster.yaml
        ```
    7. Verify status of cluster:
        ```
        kubectl get cluster -n pgvector --watch
        ```
        The output should be:
        ```
        NAME                    AGE   INSTANCES   READY   STATUS                     PRIMARY
        ai-foundry-pg-cluster   21m   3           3       Cluster in healthy state   ai-foundry-pg-cluster-1
        ```
    8. Test connectivity to cluster:
        ```
        kubectl run pg-test-pod --rm -it --image=postgres:latest --restart=Never \
            -n pgvector --env="PGHOST=ai-foundry-pg-cluster-rw.pgvector.svc.cluster.local" \
            --env="PGUSER=$(kubectl get secret ai-foundry-pg-cluster-superuser -n pgvector -o jsonpath='{.data.username}' | base64 --decode)" \
            --env="PGPASSWORD=$(kubectl get secret ai-foundry-pg-cluster-superuser -n pgvector -o jsonpath='{.data.password}' | base64 --decode)" \
            -- sh -c 'exec psql -h $PGHOST -U $PGUSER -c "\conninfo"'
        ```
        The output should be:
        ```
        You are connected to database "postgres" as user "postgres" on host "ai-foundry-pg-cluster-rw.pgvector.svc.cluster.local" (address "172.30.104.128") at port "5432".
        SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off, ALPN: none)
        pod "pg-test-pod" deleted
        ```