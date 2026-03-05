# Bunker - Kubernetes (K3s) + Tailscale Sidecar

Migração do Docker Compose para Kubernetes com rede mesh privada via Tailscale.

## Pré-requisitos

- K3s instalado (ou cluster Kubernetes)
- Tailscale: auth key em https://login.tailscale.com/admin/authkeys
- Imagem `bunker-app:latest` buildada localmente

## DNS Interno (CoreDNS)

Os serviços se resolvem automaticamente no cluster:

| Serviço   | DNS (namespace bunker)        | Porta |
|-----------|-------------------------------|-------|
| chroma    | `chroma` ou `chroma.bunker.svc.cluster.local` | 8000 |
| neo4j     | `neo4j` ou `neo4j.bunker.svc.cluster.local`   | 7474, 7687 |
| evidence  | `evidence` ou `evidence.bunker.svc.cluster.local` | 5000 |
| app       | `app` ou `app.bunker.svc.cluster.local`      | 8080 |

O app usa `CHROMA_HOST=chroma`, `NEO4J_URI=bolt://neo4j:7687`, `EVIDENCE_SERVER_HOST=evidence`.

## Tailscale (Rede Mesh)

Cada pod tem um sidecar Tailscale. Após login, os hostnames ficam acessíveis na Tailnet:

| Hostname        | Serviço   | Uso                          |
|-----------------|-----------|------------------------------|
| n8n-bunker      | app       | Principal (Telegram, agents)  |
| bunker-chroma   | chroma    | ChromaDB remoto               |
| bunker-neo4j    | neo4j     | Neo4j (7474, 7687)            |
| bunker-evidence | evidence  | Evidence Server (5000)        |

## Deploy

```bash
# 1. Build da imagem
docker build -t bunker-app:latest .

# 2. Carregar imagem no K3s (se usar containerd)
k3s ctr images import bunker-app.tar
# ou: docker save bunker-app:latest | k3s ctr images import -

# 3. Criar secrets (obrigatório antes do apply)
kubectl create secret generic tailscale-auth -n bunker \
  --from-literal=TS_AUTHKEY=tskey-xxx

kubectl create secret generic app-secrets -n bunker \
  --from-literal=TELEGRAM_BOT_TOKEN=xxx \
  --from-literal=N8N_API_KEY=xxx \
  --from-literal=N8N_API_URL=http://n8n:5678/api/v1/workflows

# 4. Aplicar manifests
kubectl apply -k infra/k8s/

# 5. Verificar pods (Tailscale pode levar ~30s para conectar)
kubectl get pods -n bunker -w
kubectl logs -n bunker -l app=chroma -c tailscale
```

## PVC (Persistência)

- `chroma-data`: 10Gi – chunks e embeddings (435+ testes)
- `neo4j-data`: 20Gi – grafo de conhecimento
- `evidence-data`: 5Gi – fotos de evidência

Os dados persistem entre restarts dos pods.

## K3s /dev/net/tun

O sidecar Tailscale usa `/dev/net/tun`. Em K3s em Linux, funciona nativamente. Em K3s no Windows (via WSL2 ou Rancher Desktop), verifique se o host expõe `/dev/net/tun`. Em alguns ambientes pode ser necessário:

```yaml
# Alternativa: usar userspace networking (sem NET_ADMIN)
# TS_USERSPACE: "true"
```

## Ordem de aplicação

1. `namespace` + `pvc` + `secrets`
2. `chroma` + `neo4j` (o app depende deles)
3. `evidence` + `app`

O Kustomization aplica tudo em ordem. O app tem `depends_on` implícito via readiness (health check no ChromaDB).
