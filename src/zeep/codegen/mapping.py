"""
Type mapping utilities for converting XSD types to Python/Pydantic types.
"""

from typing import Dict, Any
from datetime import date, time, datetime, timedelta
from decimal import Decimal


# Mapping of XSD built-in types to Python types
XSD_TO_PYTHON_TYPES: Dict[str, str] = {
    # String types
    'string': 'str',
    'normalizedString': 'str',
    'token': 'str',
    'language': 'str',
    'Name': 'str',
    'NCName': 'str',
    'ID': 'str',
    'IDREF': 'str',
    'IDREFS': 'str',
    'ENTITY': 'str',
    'ENTITIES': 'str',
    'NMTOKEN': 'str',
    'NMTOKENS': 'str',
    'anyURI': 'str',
    'QName': 'str',
    'NOTATION': 'str',
    
    # Boolean
    'boolean': 'bool',
    
    # Numeric types
    'decimal': 'Decimal',
    'float': 'float',
    'double': 'float',
    'integer': 'int',
    'positiveInteger': 'int',
    'negativeInteger': 'int',
    'nonPositiveInteger': 'int',
    'nonNegativeInteger': 'int',
    'long': 'int',
    'int': 'int',
    'short': 'int',
    'byte': 'int',
    'unsignedLong': 'int',
    'unsignedInt': 'int',
    'unsignedShort': 'int',
    'unsignedByte': 'int',
    
    # Date/Time types
    'date': 'date',
    'time': 'time',
    'dateTime': 'datetime',
    'duration': 'timedelta',
    'gYearMonth': 'str',
    'gYear': 'str',
    'gMonthDay': 'str',
    'gDay': 'str',
    'gMonth': 'str',
    
    # Binary types
    'base64Binary': 'bytes',
    'hexBinary': 'bytes',
}


def get_python_type_for_xsd_type(xsd_type_name: str, use_decimal: bool = False) -> str:
    """
    Get Python type string for an XSD type name.
    
    Args:
        xsd_type_name: Local name of XSD type (without namespace)
        use_decimal: If True, use Decimal for xs:decimal, else use float
        
    Returns:
        Python type as string (e.g., 'str', 'int', 'datetime')
    """
    python_type = XSD_TO_PYTHON_TYPES.get(xsd_type_name, 'Any')
    
    # Override decimal behavior if requested
    if not use_decimal and python_type == 'Decimal':
        python_type = 'float'
    
    return python_type


def get_import_for_type(python_type: str) -> str:
    """
    Get the import statement needed for a Python type.
    
    Args:
        python_type: Python type as string
        
    Returns:
        Import statement or empty string if no import needed
    """
    imports = {
        'date': 'from datetime import date',
        'time': 'from datetime import time',
        'datetime': 'from datetime import datetime',
        'timedelta': 'from datetime import timedelta',
        'Decimal': 'from decimal import Decimal',
    }
    
    return imports.get(python_type, '')


def collect_required_imports(types_used: set) -> list:
    """
    Collect all required import statements for a set of types.
    
    Args:
        types_used: Set of Python type strings used in generated models
        
    Returns:
        List of unique import statements
    """
    imports = set()
    imports.add('from pydantic import BaseModel, Field')
    imports.add('from typing import Optional, List, Any')
    
    for python_type in types_used:
        import_stmt = get_import_for_type(python_type)
        if import_stmt:
            imports.add(import_stmt)
    
    return sorted(imports)


def to_python_identifier(name: str) -> str:
    """
    Convert an XSD name to a valid Python identifier.
    
    Args:
        name: XSD name (may contain special characters)
        
    Returns:
        Valid Python identifier
    """
    # Replace common special characters
    identifier = name.replace('-', '_').replace('.', '_').replace(':', '_')
    
    # Ensure it doesn't start with a digit
    if identifier and identifier[0].isdigit():
        identifier = f'_{identifier}'
    
    # Avoid Python keywords
    if identifier in {'class', 'def', 'return', 'if', 'else', 'while', 
                      'for', 'import', 'from', 'as', 'pass', 'break',
                      'continue', 'raise', 'try', 'except', 'finally',
                      'with', 'lambda', 'yield', 'global', 'nonlocal'}:
        identifier = f'{identifier}_'
    
    return identifier


def to_class_name(name: str) -> str:
    """
    Convert an XSD type name to a Python class name (PascalCase).
    
    Args:
        name: XSD type name
        
    Returns:
        Python class name in PascalCase
    """
    # Remove namespace prefix if present
    if ':' in name:
        name = name.split(':')[-1]
    
    # Split on various delimiters
    parts = name.replace('-', '_').replace('.', '_').split('_')
    
    # Capitalize each part
    class_name = ''.join(part.capitalize() for part in parts if part)
    
    # Ensure it starts with a letter
    if class_name and not class_name[0].isalpha():
        class_name = f'Type{class_name}'
    
    return class_name or 'UnknownType'
