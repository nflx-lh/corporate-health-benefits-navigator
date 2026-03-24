# Cloud Deployment Runbook

Deploy-on-demand architecture for CHBN on AWS. Near-$0 when off.

## Architecture

### Default mode (CSV-only)

```
Internet → ALB (HTTP, public subnets)
              ├── /v1/*  → ECS Fargate (api, public subnet, public IP)
              └── /*     → ECS Fargate (web/nginx, public subnet, public IP)

No NAT Gateway. No private subnets. No RDS.
REPO_MODE=csv_only, APP_ENV=development (demo credentials)
```

### RDS-enabled mode (`enable_rds=true`)

```
Internet → ALB (HTTP, public subnets)
              ├── /v1/*  → ECS Fargate (api, public subnet) ──→ RDS Postgres (private subnet)
              └── /*     → ECS Fargate (web/nginx, public subnet)

No NAT Gateway. RDS in private subnets (no internet access — only reachable from ECS).
REPO_MODE=db_only, APP_ENV=development (demo credentials)
```

## Cost

| State | CSV-only | With RDS |
|-------|----------|----------|
| Running | ~$0.90/day (ALB $0.48 + Fargate $0.41) | ~$1.25/day (+ RDS db.t3.micro $0.35) |
| Off | ~$0.50/month (ECR storage only) | ~$0.50/month (ECR storage only) |

## Terraform Layout

Two **separate** Terraform states with independent lifecycles:

| Stack | Path | S3 Key | Resources |
|-------|------|--------|-----------|
| Persistent | `terraform/persistent/` | `persistent/terraform.tfstate` | ECR repos, IAM roles, SSM params |
| Demo | `terraform/demo/` | `demo/terraform.tfstate` | VPC, ALB, ECS, CloudWatch logs, RDS (optional) |

`terraform destroy` in `demo/` removes **all** demo resources (including RDS) but does **NOT** touch persistent resources.

---

## First-Time Setup

### 1. Create S3 bucket for Terraform state

```bash
aws s3 mb s3://chbn-tfstate --region ap-southeast-1
```

### 2. Deploy persistent resources

```bash
cd terraform/persistent
terraform init
terraform apply
```

### 3. Set OpenAI API key

```bash
aws ssm put-parameter --name "/chbn/dev/openai-api-key" \
  --value "sk-..." --type SecureString --overwrite --region ap-southeast-1
```

### 4. Build and push images

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com

# Pick a tag (use git SHA for traceability)
TAG=$(git rev-parse HEAD)

# Build and push API
docker build -f backend/Dockerfile.prod -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:$TAG .
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:$TAG

# Build and push Web
docker build -f frontend/Dockerfile.prod -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:$TAG ./frontend
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:$TAG
```

### 5. Configure GitHub Actions

Add these secrets to GitHub repo settings (Settings → Secrets → Actions):
- `AWS_ROLE_ARN` — the `github_actions_role_arn` output from the persistent stack
- `TF_VAR_ECR_API_URL` — ECR repo URL for API (e.g. `<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api`)
- `TF_VAR_ECR_WEB_URL` — ECR repo URL for web (e.g. `<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web`)
- `TF_VAR_ECS_EXEC_ROLE_ARN` — ECS task execution role ARN
- `TF_VAR_JWT_SECRET_ARN` — SSM parameter ARN for JWT secret
- `TF_VAR_OPENAI_API_KEY_ARN` — SSM parameter ARN for OpenAI API key

RDS is enabled by default in the workflow (`TF_VAR_enable_rds=true`) — no secret needed for this.

---

## Demo Day — CSV-only (Spin Up)

```bash
cd terraform/demo
terraform init

# Use git SHA as the image tag
TAG=$(git rev-parse HEAD)

# Pass persistent stack outputs and SHA-tagged images
terraform apply \
  -var="ecr_api_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api" \
  -var="ecr_web_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web" \
  -var="api_image=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:$TAG" \
  -var="web_image=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:$TAG" \
  -var="ecs_exec_role_arn=arn:aws:iam::<ACCOUNT_ID>:role/chbn-ecs-exec" \
  -var="jwt_secret_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/jwt-secret" \
  -var="openai_api_key_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/openai-api-key"
```

**Tip:** Save the persistent values in a `terraform.tfvars` file (gitignored) and only pass `-var="api_image=..." -var="web_image=..."` on each apply.

### Smoke test

```bash
# Health check
curl http://$(terraform output -raw alb_dns_name)/v1/health

# Frontend
curl -s http://$(terraform output -raw alb_dns_name)/ | head -5
```

---

## Demo Day — With RDS Persistence (Spin Up)

Add `enable_rds=true` to deploy with a PostgreSQL database:

```bash
cd terraform/demo
terraform init

TAG=$(git rev-parse HEAD)

terraform apply \
  -var="enable_rds=true" \
  -var="ecr_api_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api" \
  -var="ecr_web_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web" \
  -var="api_image=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:$TAG" \
  -var="web_image=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:$TAG" \
  -var="ecs_exec_role_arn=arn:aws:iam::<ACCOUNT_ID>:role/chbn-ecs-exec" \
  -var="jwt_secret_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/jwt-secret" \
  -var="openai_api_key_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/openai-api-key"
```

**What happens on first boot:**
1. Terraform creates RDS Postgres (db.t3.micro) in private subnets
2. ECS API task gets `DATABASE_URL` (via SSM SecureString) and `REPO_MODE=db_only`
3. On startup, the API auto-creates tables and seeds employees + benefit rules from CSV
4. All subsequent CRUD operations persist to Postgres

**Note:** RDS creation takes ~5-8 minutes. The ECS API task will start its health check retries during this period — it will become healthy once RDS is reachable.

### Smoke test

```bash
ALB=$(terraform output -raw alb_dns_name)

# Health check
curl http://$ALB/v1/health

# Frontend loads
curl -s http://$ALB/ | head -5

# API responds with DB-backed data
curl -s http://$ALB/v1/employees/EMP001/verify
```

### Seed benefit rules (one-off)

If `init_db()` didn't seed rules on startup (e.g. table already existed but was empty), run the seeder as a one-off ECS task:

```bash
aws ecs run-task \
  --cluster chbn-cluster \
  --task-definition chbn-api \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["<PUBLIC_SUBNET_1>", "<PUBLIC_SUBNET_2>"],
      "securityGroups": ["<ECS_SG_ID>"],
      "assignPublicIp": "ENABLED"
    }
  }' \
  --overrides '{
    "containerOverrides": [{
      "name": "api",
      "command": ["python", "-m", "app.scripts.seed_rules"]
    }]
  }' \
  --region ap-southeast-1
```

Get subnet/SG IDs from Terraform outputs or AWS Console. The seeder:
- Creates tables if missing (`CREATE TABLE IF NOT EXISTS`)
- Upserts by `rule_id` — safe to run multiple times (idempotent)
- Prints before/upserted/after counts in CloudWatch logs

**Verify seeding worked:**
```bash
# Query should return candidate_rules_count > 0
curl -s http://$ALB/v1/query-orchestrated \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"EMP001","benefit_type":"outpatient"}'
```

### Persistence test

Verify that data survives an ECS service restart:

```bash
# 1. Create a test employee via the admin API
curl -s -X POST http://$ALB/v1/admin/employees \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"TEST1","name":"Persist Test","age":30,"employment_type":"full_time","plan_tier":"premium","tenure_months":12,"dependents_count":0,"is_active":true}'

# 2. Force a new ECS deployment (restarts the API task)
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw api_service_name) \
  --force-new-deployment \
  --region ap-southeast-1

# 3. Wait for the new task to stabilise (~2-3 minutes)
aws ecs wait services-stable \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw api_service_name) \
  --region ap-southeast-1

# 4. Verify the test employee still exists
curl -s http://$ALB/v1/employees/TEST1/verify
# Expected: {"employee_id":"TEST1","name":"Persist Test","is_active":true}

# 5. Clean up test employee
curl -s -X DELETE http://$ALB/v1/admin/employees/TEST1
```

---

## After Demo (Tear Down)

```bash
cd terraform/demo
terraform destroy   # Type 'yes'
```

This destroys **all** demo resources: VPC, ALB, ECS, CloudWatch logs, and RDS (if enabled). Persistent resources (ECR, IAM, SSM) are not affected.

### Post-Destroy Checklist

- [ ] **ECS:** No clusters, services, or tasks (AWS Console → ECS)
- [ ] **EC2 → Load Balancers:** No ALBs (ALB costs ~$0.02/hr even idle)
- [ ] **RDS:** No database instances (AWS Console → RDS → Databases)
- [ ] **VPC:** No custom VPCs (only default)
- [ ] **VPC → NAT Gateways:** Confirm **none** exist (NAT costs ~$0.045/hr = $32/month)
- [ ] **CloudWatch → Log Groups:** No `/ecs/chbn-*` groups
- [ ] **EC2 → Security Groups:** No `chbn-*` groups
- [ ] **Still exists (expected):** ECR repos, IAM roles, SSM params, S3 bucket

---

## Cost Guardrails

1. **Always** run `terraform destroy` in `terraform/demo/` after every demo session
2. Verify no ALB remains: AWS Console → EC2 → Load Balancers
3. Verify no ECS services/tasks: AWS Console → ECS → Clusters
4. Verify no RDS instances: AWS Console → RDS → Databases
5. Verify no NAT Gateway: AWS Console → VPC → NAT Gateways
6. ECR image storage is the only ongoing cost (~$0.50/month)
7. Set a **billing alarm**: CloudWatch → Billing → Create alarm at $5 threshold

---

## Demo Mode Behavior

### CSV-only mode (default)
- `REPO_MODE=csv_only` — app boots without a database
- `APP_ENV=development` — auth bypass with demo credentials (HR001, EMP001–EMP003)
- When `data/index/` is empty, the retriever returns no results — the LLM explainer still generates summaries using the rules engine decision (no policy citations)
- For full citations, build the index locally first: `python scripts/build_index.py`, then rebuild the Docker image

### RDS-enabled mode
- `REPO_MODE=db_only` — app reads/writes Postgres only; no CSV fallback; fails fast if DATABASE_URL is missing
- `DATABASE_URL` injected via SSM Parameter Store (SecureString at `/chbn/dev/database-url`) — never in plaintext env vars or logs
- `APP_ENV=development` — same demo auth behaviour
- On startup, API auto-creates tables (`CREATE TABLE IF NOT EXISTS`) and seeds from CSV if tables are empty
- CRUD operations (create/update/delete employees) persist across task restarts
- Health check (`/v1/health`) works regardless of DB state

---

## Deploy-on-Demand Workflow

The GitHub Actions workflow (`.github/workflows/deploy.yml`) supports:

- **Manual trigger** (`workflow_dispatch`) — build & push images, optionally deploy to ECS
- **OIDC authentication** — no long-lived AWS credentials stored in GitHub
- **Immutable SHA tags** — images are tagged with `github.sha`, never `:latest`

### GitHub Actions role permissions (`chbn-github-actions`)

The OIDC role used by the workflow requires these IAM permissions (managed in `terraform/modules/iam/main.tf`):

| Scope | Actions | Why |
|-------|---------|-----|
| ECR | `ecr:GetAuthorizationToken`, push/pull actions | Build & push Docker images |
| S3 | `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` | Terraform state (chbn-tfstate) |
| ECS | `ecs:*` | Create/update clusters, services, task definitions |
| EC2 | VPC, subnet, route table, security group, IGW CRUD | Terraform creates VPC + private subnets for RDS |
| ALB | `elasticloadbalancing:*` | Create/manage ALB + target groups |
| RDS | `rds:*` | Create/destroy RDS instances |
| SSM | `ssm:GetParameter`, `ssm:PutParameter`, etc. | DATABASE_URL SSM parameter management |
| CloudWatch | `logs:CreateLogGroup`, `logs:PutRetentionPolicy`, etc. | ECS log groups |
| IAM | `iam:PassRole`, `iam:GetRole` | Pass ECS execution role to task definitions |

**Important:** After updating the IAM module, you must re-apply the persistent stack to push changes to AWS:
```bash
cd terraform/persistent && terraform apply
```

### How it works

1. **Build job** builds Docker images and pushes to ECR with SHA tags:
   - `chbn-api:<github.sha>`
   - `chbn-web:<github.sha>`
2. **Deploy job** runs `terraform apply` with `-var="api_image=..."` and `-var="web_image=..."` using the exact SHA-tagged URIs
3. Terraform updates ECS task definitions with the pinned image URIs
4. ECS pulls the exact images — no ambiguity, no tagless references

### Usage

1. Go to Actions → "Build & Deploy to AWS" → Run workflow
2. Set `deploy` to `true` to also update running ECS services
3. The workflow waits for ECS service stability before completing

### Verify deployed image

```bash
# Check which image the running task definition uses
aws ecs describe-task-definition \
  --task-definition chbn-api \
  --query "taskDefinition.containerDefinitions[].image" \
  --region ap-southeast-1

aws ecs describe-task-definition \
  --task-definition chbn-web \
  --query "taskDefinition.containerDefinitions[].image" \
  --region ap-southeast-1

# Both should show: <account>.dkr.ecr.<region>.amazonaws.com/chbn-api:<sha>
```

---

## RDS Technical Details

When `enable_rds=true`:
- **Instance**: `db.t3.micro` (2 vCPU, 1 GB RAM, 20 GB gp3 storage)
- **Engine**: PostgreSQL 16.4
- **Networking**: Private subnets (2 AZs), no public access, no NAT gateway
- **Security**: Ingress on port 5432 from ECS security group only
- **Credentials**: Auto-generated 24-char password via Terraform `random_password`; full `DATABASE_URL` written to SSM SecureString (`/chbn/dev/database-url`) and injected into ECS via `secrets`
- **Cleanup**: `skip_final_snapshot=true`, `deletion_protection=false` — `terraform destroy` is fast and clean
- **Backups**: Disabled (`backup_retention_period=0`) for demo cost savings

---

## ALB DNS Note

ALB DNS name changes on each `terraform apply`. No custom domain needed for demos — copy the URL from Terraform output.
