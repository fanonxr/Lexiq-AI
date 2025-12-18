# Azure OpenAI Quota Management

## Checking Current Quota

### Using Azure CLI

```bash
# List quota for your region
az cognitiveservices usage list --location <your-region> --output table

# Filter for OpenAI/gpt-4o
az cognitiveservices usage list --location westus --output json | \
  jq -r '.[] | select(.name | contains("gpt-4o") or contains("OpenAI")) | "\(.name): Current=\(.currentValue), Limit=\(.limit)"'
```

### Using Azure Portal

1. Navigate to [Azure AI Foundry Portal](https://oai.azure.com)
2. Sign in with your Azure credentials
3. Click on the **"Quotas"** tab
4. View your current usage and limits for each model and region

## Understanding Quota

The error you're seeing indicates:
- **Requested**: 10 capacity units (Tokens Per Minute in thousands)
- **Available**: 0 (quota limit is 0)
- **Current Usage**: 0

This means your subscription hasn't been granted quota for `gpt-4o` yet.

## Requesting Quota Increase

### Option 1: Azure AI Foundry Portal (Recommended)

1. Go to [Azure AI Foundry Portal](https://oai.azure.com)
2. Navigate to **"Quotas"** tab
3. Find the model you need (`gpt-4o`)
4. Click **"Request quota"** button
5. Fill out the form:
   - **Subscription ID**: Your subscription ID
   - **Region**: Your deployment region (e.g., `westus`)
   - **Model**: `gpt-4o`
   - **Desired Quota**: Start with 10-50 for development
   - **Justification**: Explain your use case
6. Submit the request

### Option 2: Azure Support

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Help + Support** → **New support request**
3. Select:
   - **Issue type**: Service and subscription limits (quotas)
   - **Subscription**: Your subscription
   - **Quota type**: Azure OpenAI Service
4. Fill out details and submit

### Option 3: Azure CLI (if available)

```bash
# Check if quota request command is available
az cognitiveservices quota request --help
```

## Development Workaround

While waiting for quota approval, you can:

1. **Reduce capacity to minimum (1)**:
   ```hcl
   scale_capacity = 1  # Minimum capacity
   ```

2. **Use a different model** that has quota:
   - `gpt-4o-mini` (often has quota available)
   - `gpt-4.1-mini`
   - `gpt-4.1-nano`

3. **Deploy without capacity** (if supported):
   - Some models support pay-as-you-go without pre-allocated capacity

## Quota Approval Timeline

- **Typical**: 1-3 business days
- **Fast track**: Can be approved within hours for some cases
- **Factors**: 
  - Subscription type
  - Region availability
  - Model popularity
  - Justification quality

## After Quota Approval

Once quota is approved:

1. **Update your configuration**:
   ```hcl
   scale_capacity = 10  # Or your approved quota
   ```

2. **Apply Terraform**:
   ```bash
   terraform apply -var-file=dev.tfvars
   ```

3. **Verify deployment**:
   ```bash
   az cognitiveservices account deployment show \
     --account-name lexiqai-openai-dev \
     --resource-group lexiqai-rg-dev \
     --name gpt-4o
   ```

## Monitoring Quota Usage

```bash
# Check current usage
az cognitiveservices usage list --location westus --output table

# Monitor in Azure Portal
# Navigate to: Azure OpenAI resource → Metrics → Quota usage
```

## Best Practices

1. **Start Small**: Request minimum needed for development (1-10)
2. **Request Early**: Submit quota requests before you need them
3. **Justify Clearly**: Explain your use case and expected traffic
4. **Monitor Usage**: Track quota usage to avoid hitting limits
5. **Plan Ahead**: Request production quotas well in advance

## Common Quota Limits

- **Free Tier**: Usually 0 (no quota by default)
- **Pay-as-you-go (S0)**: Typically 10-50 for new accounts
- **Provisioned (S1+)**: Higher limits, requires commitment

## Troubleshooting

### "Quota limit is 0"
- Your subscription hasn't been granted quota yet
- Request quota increase via Azure AI Foundry Portal

### "Insufficient quota"
- You've used all available quota
- Request increase or reduce capacity

### "Quota request pending"
- Wait for approval (1-3 business days)
- Use alternative models in the meantime

## References

- [Azure OpenAI Quota Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/quota)
- [Azure AI Foundry Portal](https://oai.azure.com)
- [Request Quota Increase Guide](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/quota)

