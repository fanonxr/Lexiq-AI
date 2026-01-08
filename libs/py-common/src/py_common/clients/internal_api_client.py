"""Base HTTP client for internal service-to-service communication with API key authentication.

This module provides a reusable client class for making authenticated HTTP requests
to internal API endpoints using the X-Internal-API-Key header.
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class InternalAPIClient:
    """
    Base HTTP client for internal service-to-service communication.
    
    Handles:
    - Automatic injection of X-Internal-API-Key header
    - Timeout configuration
    - Error handling and logging
    - Standard HTTP methods (GET, POST, PUT, DELETE, PATCH)
    
    Example:
        ```python
        from py_common.clients import InternalAPIClient
        
        client = InternalAPIClient(
            base_url="http://api-core:8000",
            api_key="your-api-key",
            timeout=30.0
        )
        
        # Make a POST request
        response = await client.post(
            "/api/v1/notifications",
            json={"message": "Hello"}
        )
        ```
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the internal API client.
        
        Args:
            base_url: Base URL of the API service (e.g., "http://api-core:8000")
            api_key: Optional internal API key for authentication
            timeout: Request timeout in seconds (default: 30.0)
            default_headers: Optional default headers to include in all requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers: Dict[str, str] = {}
        
        # Add default headers if provided
        if default_headers:
            self._headers.update(default_headers)
        
        # Add internal API key header if provided
        if api_key:
            self._headers["X-Internal-API-Key"] = api_key
            logger.debug("Internal API key configured for service-to-service authentication")
        else:
            logger.debug("No internal API key provided - requests will not include X-Internal-API-Key header")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers for a request, merging default headers with additional headers.
        
        Args:
            additional_headers: Optional additional headers to include
            
        Returns:
            Merged headers dictionary
        """
        headers = self._headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def _build_url(self, path: str) -> str:
        """
        Build full URL from base URL and path.
        
        Args:
            path: API path (e.g., "/api/v1/notifications")
            
        Returns:
            Full URL
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"
    
    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            path: API path (e.g., "/api/v1/notifications")
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            httpx.HTTPStatusError: If response status code indicates an error
            httpx.RequestError: If request fails
        """
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        
        logger.debug(f"GET {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=request_headers)
            response.raise_for_status()
            return response.json()
    
    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            path: API path (e.g., "/api/v1/notifications")
            json: Optional JSON payload
            data: Optional form data or other payload
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            httpx.HTTPStatusError: If response status code indicates an error
            httpx.RequestError: If request fails
        """
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        
        # Set Content-Type if not already set and we have JSON
        if json and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        
        logger.debug(f"POST {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if json is not None:
                response = await client.post(url, json=json, headers=request_headers)
            else:
                response = await client.post(url, content=data, headers=request_headers)
            response.raise_for_status()
            return response.json()
    
    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.
        
        Args:
            path: API path (e.g., "/api/v1/knowledge/files/{file_id}/status")
            json: Optional JSON payload
            data: Optional form data or other payload
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            httpx.HTTPStatusError: If response status code indicates an error
            httpx.RequestError: If request fails
        """
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        
        # Set Content-Type if not already set and we have JSON
        if json and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        
        logger.debug(f"PUT {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if json is not None:
                response = await client.put(url, json=json, headers=request_headers)
            else:
                response = await client.put(url, content=data, headers=request_headers)
            response.raise_for_status()
            return response.json()
    
    async def patch(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PATCH request.
        
        Args:
            path: API path
            json: Optional JSON payload
            data: Optional form data or other payload
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            httpx.HTTPStatusError: If response status code indicates an error
            httpx.RequestError: If request fails
        """
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        
        # Set Content-Type if not already set and we have JSON
        if json and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        
        logger.debug(f"PATCH {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if json is not None:
                response = await client.patch(url, json=json, headers=request_headers)
            else:
                response = await client.patch(url, content=data, headers=request_headers)
            response.raise_for_status()
            return response.json()
    
    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a DELETE request.
        
        Args:
            path: API path
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary, or None if response is empty
            
        Raises:
            httpx.HTTPStatusError: If response status code indicates an error
            httpx.RequestError: If request fails
        """
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        
        logger.debug(f"DELETE {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url, headers=request_headers)
            response.raise_for_status()
            
            # Return None for 204 No Content, otherwise parse JSON
            if response.status_code == 204 or not response.text:
                return None
            return response.json()

