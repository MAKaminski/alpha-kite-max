# Infrastructure

## Current Architecture: Lightsail Microservices

This project uses AWS Lightsail for deployments, **NOT Lambda**.

### Deployment

**Lightsail Streaming Service:**
```bash
cd lightsail/
./deploy.sh
```

See [lightsail/README.md](lightsail/README.md) for complete deployment guide.

### Terraform (Optional)

The Terraform files in this directory are minimal and optional. They can be used for:
- AWS Secrets Manager (alternative to .env files)
- Future infrastructure if needed

**Current Lightsail deployment does NOT use Terraform** - it uses the deploy.sh script instead.

### Files

- `main.tf` - AWS provider configuration
- `variables.tf` - Variable definitions
- `secrets.tf` - AWS Secrets Manager (optional)
- `outputs.tf` - Output values
- `lightsail/` - **Lightsail deployment scripts and docs** ⭐

### Migration from Lambda

Lambda infrastructure was removed in October 2025. See:
- [../CHANGES_SUMMARY.md](../CHANGES_SUMMARY.md)
- [../MICROSERVICES_ARCHITECTURE.md](../MICROSERVICES_ARCHITECTURE.md)
