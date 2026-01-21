"""
Core generator for converting Zeep XSD types to Pydantic models.
"""

from typing import Dict, List, Optional, Set, Tuple
from zeep import Client
from zeep.xsd import Schema
from zeep.xsd.types.complex import ComplexType
from zeep.xsd.types.simple import AnySimpleType
from zeep.xsd.elements import Element

from .mapping import (
    get_python_type_for_xsd_type,
    to_python_identifier,
    to_class_name,
    collect_required_imports,
)


class PydanticModelGenerator:
    """Generator for Pydantic models from XSD types"""
    
    def __init__(self, schema: Schema, use_decimal: bool = False):
        """
        Initialize generator.
        
        Args:
            schema: Zeep XSD Schema instance
            use_decimal: Use Decimal for xs:decimal instead of float
        """
        self.schema = schema
        self.use_decimal = use_decimal
        self.generated_models: Dict[str, str] = {}
        self.types_used: Set[str] = set()
    
    def generate_model_for_complex_type(self, complex_type: ComplexType) -> str:
        """
        Generate Pydantic model for a ComplexType.
        
        Args:
            complex_type: Zeep ComplexType instance
            
        Returns:
            Python source code for the Pydantic model
        """
        class_name = to_class_name(complex_type.name or 'UnknownType')
        
        # Check if already generated
        if class_name in self.generated_models:
            return self.generated_models[class_name]
        
        fields = []
        
        # Generate fields from elements
        if hasattr(complex_type, 'elements'):
            for elem_name, element in complex_type.elements:
                field_code = self._generate_field_for_element(elem_name, element)
                if field_code:
                    fields.append(field_code)
        
        # Generate fields from attributes
        if hasattr(complex_type, 'attributes'):
            for attr_name, attribute in complex_type.attributes:
                field_code = self._generate_field_for_attribute(attr_name, attribute)
                if field_code:
                    fields.append(field_code)
        
        # Build class definition
        docstring = f'"""Pydantic model for {complex_type.name or "type"}"""'
        
        if not fields:
            fields.append('pass')
        
        model_code = f'class {class_name}(BaseModel):\n'
        model_code += f'    {docstring}\n'
        for field in fields:
            model_code += f'    {field}\n'
        
        self.generated_models[class_name] = model_code
        return model_code
    
    def _generate_field_for_element(self, elem_name: str, element: Element) -> str:
        """Generate Pydantic field for an XSD element"""
        field_name = to_python_identifier(elem_name)
        python_type = self._get_type_for_element(element)
        
        # Handle cardinality
        is_optional = element.min_occurs == 0
        is_list = element.max_occurs != 1
        
        if is_list:
            python_type = f'List[{python_type}]'
            self.types_used.add('List')
        
        if is_optional:
            python_type = f'Optional[{python_type}]'
            default = ' = None'
            self.types_used.add('Optional')
        else:
            default = ''
        
        # Add Field with alias if name differs from Python identifier
        if field_name != elem_name:
            if default:
                field_def = f"{field_name}: {python_type} = Field(None, alias='{elem_name}')"
            else:
                field_def = f"{field_name}: {python_type} = Field(alias='{elem_name}')"
        else:
            field_def = f'{field_name}: {python_type}{default}'
        
        return field_def
    
    def _generate_field_for_attribute(self, attr_name: str, attribute) -> str:
        """Generate Pydantic field for an XSD attribute"""
        field_name = to_python_identifier(attr_name)
        python_type = self._get_type_for_xsd_type(attribute.type)
        
        # Attributes are typically optional
        python_type = f'Optional[{python_type}]'
        self.types_used.add('Optional')
        
        # Use @ prefix convention for XML attributes
        field_def = f"{field_name}: {python_type} = Field(None, alias='@{attr_name}')"
        return field_def
    
    def _get_type_for_element(self, element: Element) -> str:
        """Get Python type string for an element"""
        elem_type = element.type
        return self._get_type_for_xsd_type(elem_type)
    
    def _get_type_for_xsd_type(self, xsd_type) -> str:
        """Get Python type string for an XSD type"""
        # Handle ComplexType - generate nested model
        if hasattr(xsd_type, 'elements'):
            # It's a ComplexType
            if xsd_type.name:
                class_name = to_class_name(xsd_type.name)
                # Recursively generate model for nested type
                self.generate_model_for_complex_type(xsd_type)
                return class_name
            else:
                # Anonymous complex type
                return 'Dict[str, Any]'
        
        # Handle SimpleType
        if hasattr(xsd_type, 'qname') and xsd_type.qname:
            # Extract local name from QName
            type_name = xsd_type.qname.localname
            python_type = get_python_type_for_xsd_type(type_name, self.use_decimal)
            self.types_used.add(python_type)
            return python_type
        
        # Fallback
        self.types_used.add('Any')
        return 'Any'
    
    def generate_all_models(self) -> str:
        """
        Generate Pydantic models for all types in the schema.
        
        Returns:
            Python source code with all models
        """
        models = []
        
        # Collect all ComplexTypes
        for xsd_type in self.schema.types:
            if hasattr(xsd_type, 'elements'):  # Is ComplexType
                model_code = self.generate_model_for_complex_type(xsd_type)
                if model_code and model_code not in models:
                    models.append(model_code)
        
        # Generate imports
        imports = collect_required_imports(self.types_used)
        
        # Combine everything
        output = '\n'.join(imports)
        output += '\n\n\n'
        output += '\n\n'.join(models)
        
        return output


def generate_pydantic_models(
    client: Client,
    *,
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    type_names: Optional[List[str]] = None,
    include_all_types: bool = False,
    use_decimal: bool = False,
) -> str:
    """
    Generate Pydantic models from WSDL types.
    
    Args:
        client: Zeep Client instance with loaded WSDL
        service_name: Generate models for specific service (None = all services)
        operation_name: Generate models for specific operation (None = all operations)
        type_names: Generate specific types by name (None = operation-based)
        include_all_types: Generate all global types in schema
        use_decimal: Use Decimal instead of float for xs:decimal
        
    Returns:
        Python source code with Pydantic model definitions
        
    Examples:
        >>> from zeep import Client
        >>> from zeep.codegen import generate_pydantic_models
        >>> 
        >>> client = Client('http://example.com/service.wsdl')
        >>> 
        >>> # Generate models for all operations
        >>> code = generate_pydantic_models(client)
        >>> print(code)
        >>> 
        >>> # Generate models for specific operation
        >>> code = generate_pydantic_models(
        ...     client,
        ...     service_name='UserService',
        ...     operation_name='GetUser'
        ... )
        >>> 
        >>> # Generate all types
        >>> code = generate_pydantic_models(client, include_all_types=True)
    """
    schema = client.wsdl.types
    generator = PydanticModelGenerator(schema, use_decimal=use_decimal)
    
    if include_all_types:
        # Generate all types in schema
        return generator.generate_all_models()
    
    elif type_names:
        # Generate specific types by name
        models = []
        for type_name in type_names:
            try:
                # Try to get type with namespace
                xsd_type = None
                for t in schema.types:
                    if t.name == type_name:
                        xsd_type = t
                        break
                
                if xsd_type and hasattr(xsd_type, 'elements'):
                    model = generator.generate_model_for_complex_type(xsd_type)
                    models.append(model)
            except Exception:
                pass  # Type not found
        
        imports = collect_required_imports(generator.types_used)
        output = '\n'.join(imports)
        output += '\n\n\n'
        output += '\n\n'.join(models)
        return output
    
    elif operation_name:
        # Generate models for specific operation
        types_to_generate = set()
        
        for service_name_iter, service in client.wsdl.services.items():
            if service_name and service_name_iter != service_name:
                continue
            
            for port_name, port in service.ports.items():
                binding = port.binding
                
                for op_name, operation in binding.all().items():
                    if op_name == operation_name:
                        # Get input type
                        if operation.input:
                            input_type = operation.input.body.type
                            if hasattr(input_type, 'elements'):
                                types_to_generate.add(input_type)
                        
                        # Get output type
                        if operation.output:
                            output_type = operation.output.body.type
                            if hasattr(output_type, 'elements'):
                                types_to_generate.add(output_type)
        
        models = []
        for xsd_type in types_to_generate:
            model = generator.generate_model_for_complex_type(xsd_type)
            models.append(model)
        
        imports = collect_required_imports(generator.types_used)
        output = '\n'.join(imports)
        output += '\n\n\n'
        output += '\n\n'.join(models)
        return output
    
    else:
        # Generate all operation types
        return generator.generate_all_models()
