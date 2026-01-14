# DNS & Custom Domain Setup for Container Apps

## Overview

Container Apps provides automatic SSL/TLS certificates via Let's Encrypt for custom domains. This document explains how to configure custom domains for your Container Apps.

## Current Configuration

The following services support custom domains:
- **API Core** - Public API endpoint
- **Voice Gateway** - Twilio WebSocket endpoint
- **Integration Worker Webhooks** - External webhook receiver

## Setup Steps

### 1. Configure Custom Domains in Terraform

Add custom domain variables to your `terraform.tfvars` or environment-specific tfvars file:

```hcl
# Example: prod.tfvars
api_core_custom_domain            = "api.lexiqai.com"
voice_gateway_custom_domain      = "voice.lexiqai.com"
integration_webhooks_custom_domain = "webhooks.lexiqai.com"
```

### 2. Deploy Infrastructure

```bash
terraform apply -var-file=prod.tfvars
```

### 3. Configure DNS Records

After deployment, you need to create DNS records pointing to your Container Apps. Container Apps will provide you with the target hostname.

#### Option A: Using Azure DNS (Recommended for Azure-managed domains)

If you manage your DNS through Azure DNS, you can create the DNS zone and records:

```hcl
# Optional: Create Azure DNS Zone
resource "azurerm_dns_zone" "main" {
  name                = "lexiqai.com"
  resource_group_name = azurerm_resource_group.main.name
}

# CNAME records for custom domains
resource "azurerm_dns_cname_record" "api_core" {
  name                = "api"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_container_app.api_core.ingress[0].fqdn
}
```

#### Option B: Using External DNS Provider

1. **Get the Container Apps FQDN** from Terraform outputs:
   ```bash
   terraform output api_core_hostname
   # Output: lexiqai-api-core-prod.azurecontainerapps.io
   ```

2. **Create CNAME records** in your DNS provider:
   - `api.lexiqai.com` → CNAME → `lexiqai-api-core-prod.azurecontainerapps.io`
   - `voice.lexiqai.com` → CNAME → `lexiqai-voice-gateway-prod.azurecontainerapps.io`
   - `webhooks.lexiqai.com` → CNAME → `lexiqai-integration-worker-webhooks-prod.azurecontainerapps.io`

3. **Wait for DNS propagation** (usually 5-15 minutes)

4. **Container Apps will automatically**:
   - Detect the DNS record
   - Request Let's Encrypt certificate
   - Enable HTTPS (this may take 10-15 minutes)

### 4. Verify SSL Certificate

After DNS propagation and certificate provisioning (can take 10-15 minutes):

```bash
# Check certificate status
az containerapp hostname list \
  --name lexiqai-api-core-prod \
  --resource-group lexiqai-rg-prod

# Test HTTPS
curl -I https://api.lexiqai.com/health
```

## SSL/TLS Certificate Details

- **Certificate Type**: Managed (Let's Encrypt)
- **Automatic Renewal**: Yes (Container Apps handles renewal automatically)
- **Certificate Provisioning Time**: 10-15 minutes after DNS is configured
- **HTTPS Only**: Enabled by default (`allow_insecure = false`)

## Default FQDN (No Custom Domain)

If you don't configure custom domains, Container Apps provides default FQDNs:
- Format: `{app-name}.{environment}.azurecontainerapps.io`
- Example: `lexiqai-api-core-prod.azurecontainerapps.io`
- SSL/TLS: Automatically enabled
- No DNS configuration needed

## Troubleshooting

### Certificate Not Provisioning

1. **Verify DNS records**:
   ```bash
   dig api.lexiqai.com CNAME
   # Should return the Container Apps FQDN
   ```

2. **Check DNS propagation**:
   - Use https://dnschecker.org to verify DNS is propagated globally

3. **Check Container Apps logs**:
   ```bash
   az containerapp logs show \
     --name lexiqai-api-core-prod \
     --resource-group lexiqai-rg-prod
   ```

### Certificate Status

Check certificate status in Azure Portal:
1. Navigate to Container App
2. Go to "Custom domains" section
3. Verify certificate status is "Ready"

## Production Recommendations

1. **Use Custom Domains** for production (better branding, easier to remember)
2. **Use Azure DNS** if managing DNS through Azure (simpler integration)
3. **Monitor Certificate Expiry** (though Container Apps handles renewal automatically)
4. **Set up DNS Alerts** to monitor DNS record changes

## References

- [Container Apps Custom Domains](https://learn.microsoft.com/en-us/azure/container-apps/custom-domains-certificates)
- [Azure DNS Documentation](https://learn.microsoft.com/en-us/azure/dns/)
