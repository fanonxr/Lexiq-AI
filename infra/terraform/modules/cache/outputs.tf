output "cache_id" {
  description = "ID of the Redis cache"
  value       = azurerm_redis_cache.main.id
}

output "cache_name" {
  description = "Name of the Redis cache"
  value       = azurerm_redis_cache.main.name
}

output "hostname" {
  description = "Hostname of the Redis cache"
  value       = azurerm_redis_cache.main.hostname
  sensitive   = true
}

output "port" {
  description = "Port number for non-SSL connections"
  value       = azurerm_redis_cache.main.port
}

output "ssl_port" {
  description = "Port number for SSL connections"
  value       = azurerm_redis_cache.main.ssl_port
}

output "primary_access_key" {
  description = "Primary access key for Redis"
  value       = azurerm_redis_cache.main.primary_access_key
  sensitive   = true
}

output "secondary_access_key" {
  description = "Secondary access key for Redis"
  value       = azurerm_redis_cache.main.secondary_access_key
  sensitive   = true
}

output "primary_connection_string" {
  description = "Primary connection string (without password, use primary_access_key)"
  value       = "redis://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}"
  sensitive   = true
}

