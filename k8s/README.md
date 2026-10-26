# Optional Kubernetes manifests

These manifests run the static-site image from the separate Docker change. They do not create a cluster, public load balancer, ingress, cloud IAM, or production deployment. The Service is internal `ClusterIP` only.

For a local `kind` cluster, after merging the Docker PR:

```sh
docker build --tag devobs-web:local .
kind load docker-image devobs-web:local
kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml -f k8s/service.yaml
kubectl rollout status deployment/devobs-web
kubectl port-forward service/devobs-web 8080:80
```

Open <http://127.0.0.1:8080>. Replace the local image tag with an immutable image reference only after a separate registry publication and access-control design. Do not apply to a production cluster as part of this change. See the official [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Service](https://kubernetes.io/docs/concepts/services-networking/service/), and [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) references.
