# Secret Variables
# These variables should be set via environment variables (TF_VAR_*) or passed via -var flags
# NEVER commit actual secret values to version control

# Google OAuth Secrets
variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# Twilio Secrets
variable "twilio_account_token" {
  description = "Twilio Account Token (Auth Token)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "twilio_api_key" {
  description = "Twilio API Key (optional, if using API keys instead of Auth Token)"
  type        = string
  sensitive   = true
  default     = ""
}

# Stripe Secrets
variable "stripe_publishable_key" {
  description = "Stripe publishable key (not a secret, but kept here for consistency)"
  type        = string
  sensitive   = false # Publishable keys are safe to be public
  default     = ""
}

variable "stripe_webhook_secret" {
  description = "Stripe webhook signing secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_secret_key" {
  description = "Stripe API secret key"
  type        = string
  sensitive   = true
  default     = ""
}

# Deepgram API Key
variable "deepgram_api_key" {
  description = "Deepgram API key for speech-to-text"
  type        = string
  sensitive   = true
  default     = ""
}

# Cartesia API Key
variable "cartesia_api_key" {
  description = "Cartesia API key for text-to-speech"
  type        = string
  sensitive   = true
  default     = ""
}

# Internal API Key (for service-to-service authentication)
variable "internal_api_key" {
  description = "Internal API key for service-to-service authentication. Generate a strong random string."
  type        = string
  sensitive   = true
  default     = ""
}

# JWT Secret Key (for token signing)
variable "jwt_secret_key" {
  description = "JWT secret key for token signing. Generate a strong random string (at least 32 characters)."
  type        = string
  sensitive   = true
  default     = ""
}

# Azure AD B2C Client Secret (if different from main Azure AD client secret)
variable "azure_ad_b2c_client_secret" {
  description = "Azure AD B2C client secret (if using B2C separately from main Azure AD)"
  type        = string
  sensitive   = true
  default     = ""
}

# Anthropic API Key
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude models"
  type        = string
  sensitive   = true
  default     = ""
}

# Groq API Key
variable "groq_api_key" {
  description = "Groq API key for fast inference"
  type        = string
  sensitive   = true
  default     = ""
}

# Qdrant API Key (optional - for Qdrant Cloud)
variable "qdrant_api_key" {
  description = "Qdrant API key (optional - only needed for Qdrant Cloud)"
  type        = string
  sensitive   = true
  default     = ""
}

# RabbitMQ Password
variable "rabbitmq_password" {
  description = "RabbitMQ default user password. Generate a strong random string."
  type        = string
  sensitive   = true
  default     = ""
}

# Redis Password
variable "redis_password" {
  description = "Redis password. Generate a strong random string."
  type        = string
  sensitive   = true
  default     = ""
}

# Webhook Secret (for integration worker webhooks)
# NOTE: This is currently NOT USED in the application code
# Microsoft Graph webhooks use validation tokens in headers, not shared secrets
# Google Calendar webhooks (Phase 5) are not yet implemented
# Uncomment and use this if you implement webhook signature validation in the future
# variable "webhook_secret" {
#   description = "Webhook secret for validating incoming webhooks from Microsoft Graph, Google Calendar, etc."
#   type        = string
#   sensitive   = true
#   default     = ""
# }

# Azure AD Client Secret (if not using auth module or need separate value)
variable "azure_ad_client_secret" {
  description = "Azure AD client secret (if not using auth module or need separate value)"
  type        = string
  sensitive   = true
  default     = ""
}
