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
REPO_MODE=db_first, APP_ENV=development (demo credentials)
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

# Build and push API
docker build -f backend/Dockerfile.prod -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:latest .
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api:latest

# Build and push Web
docker build -f frontend/Dockerfile.prod -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:latest ./frontend
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web:latest
```

### 5. Configure GitHub Actions

Add this secret to GitHub repo settings:
- `AWS_ROLE_ARN` — the `github_actions_role_arn` output from the persistent stack

---

## Demo Day — CSV-only (Spin Up)

```bash
cd terraform/demo
terraform init

# Pass persistent stack outputs as variables
terraform apply \
  -var="ecr_api_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api" \
  -var="ecr_web_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web" \
  -var="ecs_exec_role_arn=arn:aws:iam::<ACCOUNT_ID>:role/chbn-ecs-exec" \
  -var="jwt_secret_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/jwt-secret" \
  -var="openai_api_key_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/openai-api-key"
```

**Tip:** Save these in a `terraform.tfvars` file (gitignored) so you only need `terraform apply`.

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

terraform apply \
  -var="enable_rds=true" \
  -var="ecr_api_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-api" \
  -var="ecr_web_url=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/chbn-web" \
  -var="ecs_exec_role_arn=arn:aws:iam::<ACCOUNT_ID>:role/chbn-ecs-exec" \
  -var="jwt_secret_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/jwt-secret" \
  -var="openai_api_key_arn=arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/chbn/dev/openai-api-key"
```

**What happens on first boot:**
1. Terraform creates RDS Postgres (db.t3.micro) in private subnets
2. ECS API task gets `DATABASE_URL` and `REPO_MODE=db_first`
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
- `REPO_MODE=db_first` — app reads/writes Postgres, falls back to CSV on error
- `APP_ENV=development` — same demo auth behaviour
- On startup, API auto-creates tables (`CREATE TABLE IF NOT EXISTS`) and seeds from CSV if tables are empty
- CRUD operations (create/update/delete employees) persist across task restarts
- Health check (`/v1/health`) works regardless of DB state

---

## CI/CD

The GitHub Actions workflow (`.github/workflows/deploy.yml`) supports:

- **Manual trigger** (`workflow_dispatch`) — build & push images, optionally deploy to ECS
- **OIDC authentication** — no long-lived AWS credentials stored in GitHub
- Images are tagged with both git SHA and `latest`

### Usage

1. Go to Actions → "Build & Deploy to AWS" → Run workflow
2. Set `deploy` to `true` to also update running ECS services
3. The workflow waits for ECS service stability before completing

---

## RDS Technical Details

When `enable_rds=true`:
- **Instance**: `db.t3.micro` (2 vCPU, 1 GB RAM, 20 GB gp3 storage)
- **Engine**: PostgreSQL 16.4
- **Networking**: Private subnets (2 AZs), no public access, no NAT gateway
- **Security**: Ingress on port 5432 from ECS security group only
- **Credentials**: Auto-generated 24-char password via Terraform `random_password`
- **Cleanup**: `skip_final_snapshot=true`, `deletion_protection=false` — `terraform destroy` is fast and clean
- **Backups**: Disabled (`backup_retention_period=0`) for demo cost savings

---

## ALB DNS Note

ALB DNS name changes on each `terraform apply`. No custom domain needed for demos — copy the URL from Terraform output.
