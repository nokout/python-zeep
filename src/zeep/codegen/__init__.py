"""
Zeep Code Generation Module

This module provides utilities for generating Pydantic models from WSDL/XSD types.
It enables users to create type-safe Python models from SOAP service definitions.

Example:
    >>> from zeep import Client
    >>> from zeep.codegen import generate_pydantic_models
    >>> 
    >>> client = Client('http://example.com/service.wsdl')
    >>> code = generate_pydantic_models(client, operation_name='GetUser')
    >>> print(code)
"""

from .generator import generate_pydantic_models

__all__ = ['generate_pydantic_models']
