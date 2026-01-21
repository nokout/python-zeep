# Research: Pydantic Model Generation from WSDL Types

## Executive Summary

This document presents comprehensive research findings for implementing Pydantic model generation from WSDL/XSD types in the Zeep library. The research demonstrates that the proposed approach is **technically feasible** and can be implemented with minimal changes to the existing codebase by creating a new `zeep.codegen` module.

### Key Findings

✅ **Feasibility**: Zeep's existing type system provides complete introspection capabilities  
✅ **Reusability**: All required components already exist in `zeep.xsd` module  
✅ **Integration**: Can be added as a standalone module without modifying core code  
✅ **Coverage**: Supports ComplexTypes, SimpleTypes, enums, restrictions, and nested types

---

## Part 1: Understanding Zeep's Type System

### 1.1 Architecture Overview

Zeep separates WSDL service definitions from XSD type definitions:

```
Client → WSDL Document → Services → Ports → Bindings → Operations
                      ↓
                   Schema → Types (ComplexType/SimpleType) → Elements/Attributes
```

**Key Components:**
- **`zeep.wsdl.Document`**: Entry point for WSDL parsing
- **`zeep.xsd.Schema`**: Container for all XSD type definitions
- **`zeep.xsd.types.ComplexType`**: Structured types with elements and attributes
- **`zeep.xsd.types.simple.AnySimpleType`**: Primitive types, enums, restrictions
- **`zeep.xsd.elements.Element`**: Type members with cardinality constraints

### 1.2 Type System Representation

#### ComplexType Structure

```python
# From zeep/xsd/types/complex.py
class ComplexType(Type):
    qname: QName              # Qualified name with namespace
    name: str                 # Local name
    _element: Indicator       # Sequence/Choice/All/Group container
    _attributes: List[Attr]   # List of attributes
    _extension: Type          # Base type if extended
    _restriction: Type        # Base type if restricted
    
    @property
    def elements(self) -> List[Tuple[str, Element]]:
        """Flattened list of (name, Element) tuples"""
        
    @property  
    def attributes(self) -> List[Tuple[str, Attribute]]:
        """List of (name, Attribute) tuples"""
```

**Example Usage:**
```python
from zeep import Client

client = Client('http://example.com/service.wsdl')
schema = client.wsdl.types

# Get a ComplexType
user_type = schema.get_type('{http://example.com}User')

# Inspect elements
for elem_name, element in user_type.elements:
    print(f"{elem_name}: {element.type}")
    print(f"  Optional: {element.is_optional}")
    print(f"  Multiple: {element.accepts_multiple}")
```

#### SimpleType & Enumerations

```python
# From zeep/xsd/types/simple.py and builtins.py
class AnySimpleType(AnyType):
    qname: QName
    name: str
    accepted_types: tuple  # Python types this XSD type accepts
    
# Built-in types map to Python types:
String → str
Boolean → bool
Integer → int
Decimal → decimal.Decimal
Date → datetime.date
DateTime → datetime.datetime
```

**Enumeration Example:**
```python
# Enums are SimpleType with restriction facets
enum_type = schema.get_type('{http://example.com}StatusEnum')
# Restriction contains enumeration values
```

#### Element with Cardinality

```python
# From zeep/xsd/elements/element.py
class Element:
    name: str                # Element name
    type: Type              # ComplexType or SimpleType
    min_occurs: int         # 0, 1, or more
    max_occurs: int|str     # int or "unbounded"
    nillable: bool          # Can be None?
    default: Any            # Default value
    
    @property
    def is_optional(self) -> bool:
        return self.min_occurs == 0
        
    @property
    def accepts_multiple(self) -> bool:
        return self.max_occurs != 1
```

### 1.3 Accessing Types from WSDL

```python
from zeep import Client

# Load WSDL
client = Client('http://example.com/service.wsdl')

# Access schema with all types
schema = client.wsdl.types

# Get all global types
for xsd_type in schema.types:
    print(f"Type: {xsd_type.qname}")
    
# Get specific type
user_type = schema.get_type('{http://example.com}User')

# Access operations and their types
for service_name, service in client.wsdl.services.items():
    for port_name, port in service.ports.items():
        binding = port.binding
        for op_name, operation in binding.all().items():
            # Get input type
            input_elem = operation.input.body
            input_type = input_elem.type
            
            # Get output type
            output_elem = operation.output.body
            output_type = output_elem.type
```

---

## Part 2: Design - XSD to Pydantic Mapping

### 2.1 Type Mapping Strategy

| XSD Type | Pydantic Type | Notes |
|----------|---------------|-------|
| `xs:string` | `str` | Direct mapping |
| `xs:boolean` | `bool` | Direct mapping |
| `xs:integer`, `xs:int`, `xs:long` | `int` | Direct mapping |
| `xs:decimal`, `xs:float`, `xs:double` | `float` or `Decimal` | Configurable |
| `xs:date` | `datetime.date` | Import from datetime |
| `xs:dateTime` | `datetime.datetime` | Import from datetime |
| `xs:time` | `datetime.time` | Import from datetime |
| `xs:duration` | `datetime.timedelta` | Import from datetime |
| `xs:base64Binary` | `bytes` | Direct mapping |
| ComplexType | Nested `BaseModel` | Recursive generation |
| SimpleType with enum | `Literal[...]` or `Enum` | Enum values as literals |
| SimpleType with restriction | `Annotated[type, Field(...)]` | Constraints via Field |
| Element (minOccurs=0) | `Optional[T]` | Nullable field |
| Element (maxOccurs>1) | `List[T]` | Multiple values |
| Attribute | Field with `alias` | XML attribute mapping |

### 2.2 Algorithm: XSD ComplexType → Pydantic Model

```python
def generate_pydantic_model(complex_type: ComplexType, schema: Schema) -> str:
    """
    Generate Pydantic model from XSD ComplexType
    
    Steps:
    1. Generate class name from type.name
    2. For each element in type.elements:
       a. Determine Python type from element.type
       b. Handle cardinality (Optional, List)
       c. Create Field with validation constraints
    3. For each attribute in type.attributes:
       a. Map to Pydantic field with alias
    4. Recursively generate nested ComplexTypes
    5. Return complete model definition
    """
    
    class_name = to_class_name(complex_type.name)
    fields = []
    
    # Process elements
    for elem_name, element in complex_type.elements:
        python_type = map_xsd_type_to_python(element.type, schema)
        
        # Handle cardinality
        if element.accepts_multiple:
            python_type = f"List[{python_type}]"
        if element.is_optional:
            python_type = f"Optional[{python_type}]"
            default = "None"
        else:
            default = "..."  # Required field
            
        # Create field
        field_def = f"{elem_name}: {python_type} = {default}"
        fields.append(field_def)
    
    # Process attributes
    for attr_name, attribute in complex_type.attributes:
        python_type = map_xsd_type_to_python(attribute.type, schema)
        field_def = f"{attr_name}: {python_type} = Field(alias='@{attr_name}')"
        fields.append(field_def)
    
    # Generate class
    model = f"class {class_name}(BaseModel):\n"
    for field in fields:
        model += f"    {field}\n"
    
    return model
```

### 2.3 Handling Nested Types

```python
def collect_dependent_types(complex_type: ComplexType, schema: Schema) -> Set[ComplexType]:
    """
    Recursively collect all dependent ComplexTypes
    This ensures we generate all nested models in correct order
    """
    dependencies = set()
    
    for elem_name, element in complex_type.elements:
        elem_type = element.type
        if hasattr(elem_type, 'elements'):  # Is ComplexType
            dependencies.add(elem_type)
            dependencies.update(collect_dependent_types(elem_type, schema))
    
    return dependencies

def generate_all_models(root_type: ComplexType, schema: Schema) -> str:
    """
    Generate all models in dependency order (bottom-up)
    """
    all_types = collect_dependent_types(root_type, schema)
    all_types.add(root_type)
    
    # Sort by dependencies (simple topological sort)
    sorted_types = topological_sort(all_types)
    
    models = []
    for xsd_type in sorted_types:
        model = generate_pydantic_model(xsd_type, schema)
        models.append(model)
    
    return "\n\n".join(models)
```

### 2.4 Handling SimpleType Restrictions & Enums

```python
def map_simple_type(simple_type: AnySimpleType, schema: Schema) -> str:
    """
    Map XSD SimpleType to Pydantic type with constraints
    """
    # Check for enum restriction
    if has_enumeration(simple_type):
        enum_values = get_enumeration_values(simple_type)
        return f"Literal[{', '.join(repr(v) for v in enum_values)}]"
    
    # Check for other restrictions (minInclusive, maxInclusive, pattern, etc.)
    base_type = get_python_type(simple_type)
    constraints = extract_constraints(simple_type)
    
    if constraints:
        # Use Annotated with Field constraints
        constraint_args = ", ".join(f"{k}={v}" for k, v in constraints.items())
        return f"Annotated[{base_type}, Field({constraint_args})]"
    
    return base_type

def extract_constraints(simple_type: AnySimpleType) -> Dict[str, Any]:
    """Extract validation constraints from XSD restrictions"""
    constraints = {}
    
    if hasattr(simple_type, '_restriction'):
        restriction = simple_type._restriction
        if hasattr(restriction, 'min_inclusive'):
            constraints['ge'] = restriction.min_inclusive
        if hasattr(restriction, 'max_inclusive'):
            constraints['le'] = restriction.max_inclusive
        if hasattr(restriction, 'min_length'):
            constraints['min_length'] = restriction.min_length
        if hasattr(restriction, 'max_length'):
            constraints['max_length'] = restriction.max_length
        if hasattr(restriction, 'pattern'):
            constraints['pattern'] = restriction.pattern
    
    return constraints
```

---

## Part 3: Implementation Design

### 3.1 Module Structure

```
src/zeep/
└── codegen/
    ├── __init__.py           # Public API exports
    ├── generator.py          # Core Pydantic generation logic
    ├── mapping.py            # XSD → Python type mapping
    ├── formatting.py         # Code formatting utilities
    └── cli.py                # Interactive CLI interface
```

### 3.2 Utility Module API

```python
# zeep/codegen/__init__.py
from .generator import generate_pydantic_models

__all__ = ['generate_pydantic_models']
```

```python
# zeep/codegen/generator.py
from typing import Dict, List, Optional, Set
from zeep import Client
from zeep.xsd import Schema, ComplexType
from pydantic import BaseModel

def generate_pydantic_models(
    client: Client,
    *,
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    type_names: Optional[List[str]] = None,
    include_all_types: bool = False,
    generate_enums: bool = True,
    use_decimal: bool = False,
    add_examples: bool = True,
) -> str:
    """
    Generate Pydantic models from WSDL types.
    
    Args:
        client: Zeep Client instance with loaded WSDL
        service_name: Generate models for specific service (None = all services)
        operation_name: Generate models for specific operation (None = all operations)
        type_names: Generate specific types by name (None = operation-based)
        include_all_types: Generate all global types in schema
        generate_enums: Convert XSD enumerations to Python Enum classes
        use_decimal: Use Decimal instead of float for xs:decimal
        add_examples: Add example values in model docstrings
        
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
        >>> 
        >>> # Generate models for specific operation
        >>> code = generate_pydantic_models(
        ...     client,
        ...     service_name='UserService',
        ...     operation_name='GetUser'
        ... )
        >>> 
        >>> # Generate specific types
        >>> code = generate_pydantic_models(
        ...     client,
        ...     type_names=['User', 'Address', 'Order']
        ... )
    """
    pass

def generate_pydantic_model_classes(
    client: Client,
    **kwargs
) -> Dict[str, type[BaseModel]]:
    """
    Generate actual Pydantic model classes (not just source code).
    
    Returns:
        Dict mapping model names to Pydantic BaseModel classes
        
    Examples:
        >>> models = generate_pydantic_model_classes(client)
        >>> User = models['User']
        >>> user = User(name='John', email='john@example.com')
        >>> print(user.model_dump())
    """
    pass
```

### 3.3 Interactive CLI Interface

```python
# zeep/codegen/cli.py
import click
from zeep import Client
from .generator import generate_pydantic_models

@click.group()
def codegen():
    """Code generation utilities for Zeep"""
    pass

@codegen.command()
@click.argument('wsdl_url')
@click.option('--service', '-s', help='Service name')
@click.option('--operation', '-o', help='Operation name')
@click.option('--output', '-O', type=click.File('w'), default='-',
              help='Output file (default: stdout)')
@click.option('--all-types', is_flag=True, help='Generate all types')
@click.option('--no-enums', is_flag=True, help='Use Literal instead of Enum')
@click.option('--decimal', is_flag=True, help='Use Decimal for xs:decimal')
def generate(wsdl_url, service, operation, output, all_types, no_enums, decimal):
    """
    Generate Pydantic models from WSDL
    
    Examples:
        python -m zeep.codegen generate http://example.com/service.wsdl
        python -m zeep.codegen generate service.wsdl -s UserService -o GetUser
        python -m zeep.codegen generate service.wsdl --all-types -O models.py
    """
    client = Client(wsdl_url)
    
    code = generate_pydantic_models(
        client,
        service_name=service,
        operation_name=operation,
        include_all_types=all_types,
        generate_enums=not no_enums,
        use_decimal=decimal,
    )
    
    output.write(code)
    click.echo(f"Generated Pydantic models", err=True)

@codegen.command()
@click.argument('wsdl_url')
def browse(wsdl_url):
    """
    Interactive browser for WSDL operations and types
    
    Allows user to:
    - Browse available services
    - View operations and their signatures
    - Select operations to generate models for
    - Fill in request templates
    """
    client = Client(wsdl_url)
    
    # Interactive menu system
    while True:
        click.echo("\n=== WSDL Browser ===")
        click.echo("1. List Services")
        click.echo("2. List Operations")
        click.echo("3. Generate Models")
        click.echo("4. Fill Request Template")
        click.echo("5. Exit")
        
        choice = click.prompt("Select option", type=int)
        
        if choice == 1:
            list_services(client)
        elif choice == 2:
            list_operations(client)
        elif choice == 3:
            generate_interactive(client)
        elif choice == 4:
            fill_template(client)
        elif choice == 5:
            break

def list_services(client: Client):
    """List all services in WSDL"""
    click.echo("\nAvailable Services:")
    for i, (name, service) in enumerate(client.wsdl.services.items(), 1):
        click.echo(f"{i}. {name}")
        for port_name in service.ports:
            click.echo(f"   └─ Port: {port_name}")

def list_operations(client: Client):
    """List all operations"""
    click.echo("\nAvailable Operations:")
    for service_name, service in client.wsdl.services.items():
        click.echo(f"\n{service_name}:")
        for port_name, port in service.ports.items():
            binding = port.binding
            for op_name, operation in binding.all().items():
                abstract = operation.abstract
                input_sig = operation.input.body.type.signature(client.wsdl.types)
                output_sig = operation.output.body.type.signature(client.wsdl.types)
                click.echo(f"  {op_name}")
                click.echo(f"    Input:  {input_sig}")
                click.echo(f"    Output: {output_sig}")

def generate_interactive(client: Client):
    """Interactive model generation"""
    services = list(client.wsdl.services.keys())
    
    # Select service
    click.echo("\nSelect Service:")
    for i, name in enumerate(services, 1):
        click.echo(f"{i}. {name}")
    service_idx = click.prompt("Service number", type=int) - 1
    service_name = services[service_idx]
    
    # Select operation
    service = client.wsdl.services[service_name]
    port = next(iter(service.ports.values()))
    operations = list(port.binding.all().keys())
    
    click.echo("\nSelect Operation:")
    for i, name in enumerate(operations, 1):
        click.echo(f"{i}. {name}")
    op_idx = click.prompt("Operation number", type=int) - 1
    operation_name = operations[op_idx]
    
    # Generate models
    code = generate_pydantic_models(
        client,
        service_name=service_name,
        operation_name=operation_name,
    )
    
    # Save or display
    save = click.confirm("\nSave to file?")
    if save:
        filename = click.prompt("Filename", default=f"{operation_name.lower()}_models.py")
        with open(filename, 'w') as f:
            f.write(code)
        click.echo(f"Saved to {filename}")
    else:
        click.echo("\n" + code)

def fill_template(client: Client):
    """Interactive template filling"""
    # Generate Pydantic models dynamically
    models = generate_pydantic_model_classes(client)
    
    # Prompt user for values
    click.echo("\nFill in request template:")
    # ... interactive prompting ...
    
    # Create instance
    # user = User(name=..., email=...)
    
    # Serialize to YAML
    # yaml.dump(user.model_dump())
```

### 3.4 Usage Examples

**Example 1: Generate models for specific operation**
```python
from zeep import Client
from zeep.codegen import generate_pydantic_models

client = Client('http://www.dneonline.com/calculator.asmx?WSDL')

code = generate_pydantic_models(
    client,
    operation_name='Add'
)

print(code)
```

**Output:**
```python
from pydantic import BaseModel
from typing import Optional

class Add(BaseModel):
    """Request for Add operation"""
    intA: int
    intB: int

class AddResponse(BaseModel):
    """Response for Add operation"""
    AddResult: int
```

**Example 2: Generate all types and fill template**
```python
from zeep import Client
from zeep.codegen import generate_pydantic_model_classes
import yaml

client = Client('http://example.com/user-service.wsdl')

# Generate Pydantic classes
models = generate_pydantic_model_classes(client)

# Use as template
CreateUserRequest = models['CreateUserRequest']

# Fill in interactively or programmatically
request = CreateUserRequest(
    username='john_doe',
    email='john@example.com',
    firstName='John',
    lastName='Doe',
    birthDate='1990-01-15'
)

# Export to YAML for user to review/edit
yaml_output = yaml.dump(request.model_dump())
print(yaml_output)
```

**Output YAML:**
```yaml
username: john_doe
email: john@example.com
firstName: John
lastName: Doe
birthDate: '1990-01-15'
```

---

## Part 4: Technical Feasibility Assessment

### 4.1 Viability with Zeep's Architecture

✅ **FULLY VIABLE** - The approach is completely compatible with Zeep's architecture:

1. **No Core Modifications Required**: Implementation is additive only
2. **Complete Introspection**: All necessary type metadata is accessible
3. **Well-Defined APIs**: Clear boundaries between WSDL, XSD, and codegen modules
4. **Proven Patterns**: Similar to existing `zeep.xsd.printer` for type signatures

### 4.2 Technical Challenges & Solutions

| Challenge | Solution | Complexity |
|-----------|----------|------------|
| Circular type references | Topological sort + forward references | Medium |
| Namespace handling | Include namespace in class names or use qualified names | Low |
| XSD choice/all indicators | Generate Union types or optional groups | Medium |
| XSD any/anyAttribute | Use `Dict[str, Any]` or custom validation | Low |
| Complex restrictions | Extract facets and map to Field constraints | Medium |
| Extension/Restriction | Handle only if explicitly requested (excluded per requirements) | N/A |

### 4.3 Limitations

1. **No Inheritance Handling**: As per requirements, we skip XSD extension/restriction inheritance
2. **Namespace Collisions**: Type names may conflict if multiple namespaces define same name
   - Solution: Prefix with namespace or use `model_config` with namespace metadata
3. **XSD Choice**: Pydantic doesn't have native XSD choice support
   - Solution: Make all choice elements optional or use Union types
4. **Validation Gaps**: Some XSD constraints don't map perfectly to Pydantic
   - Solution: Document limitations and provide custom validators

### 4.4 Performance Considerations

- **Generation Time**: O(n) where n = number of types, negligible for typical WSDLs
- **Memory**: Minimal overhead, only holds generated code strings
- **Runtime**: No runtime impact on existing zeep functionality

---

## Part 5: Proof of Concept

### 5.1 Basic Implementation

See `src/zeep/codegen/generator.py` for full implementation.

### 5.2 Test with Real WSDL

```python
# Example with public WSDL
from zeep import Client
from zeep.codegen import generate_pydantic_models

# Load calculator WSDL
client = Client('http://www.dneonline.com/calculator.asmx?WSDL')

# Generate models
code = generate_pydantic_models(client, operation_name='Add')

print("Generated Pydantic Models:")
print("=" * 60)
print(code)
print("=" * 60)

# Verify generated code compiles
exec(compile(code, '<generated>', 'exec'))
print("✓ Code compiles successfully")
```

---

## Part 6: Implementation Roadmap

### Phase 1: Core Generator (1-2 weeks)
- [ ] Create `zeep.codegen` module structure
- [ ] Implement type mapping logic (`mapping.py`)
- [ ] Implement ComplexType → Pydantic model generator
- [ ] Implement SimpleType → Python type mapping
- [ ] Handle cardinality (Optional, List)
- [ ] Write unit tests

### Phase 2: Advanced Features (1 week)
- [ ] Enum generation support
- [ ] Constraint extraction (min/max, pattern, length)
- [ ] Nested type dependency resolution
- [ ] Circular reference handling with forward refs
- [ ] Namespace handling

### Phase 3: API & CLI (1 week)
- [ ] Public API implementation (`generate_pydantic_models`)
- [ ] CLI command: `python -m zeep.codegen generate`
- [ ] CLI command: `python -m zeep.codegen browse`
- [ ] Integration tests with real WSDLs

### Phase 4: Polish & Documentation (1 week)
- [ ] Code formatting and optimization
- [ ] Comprehensive docstrings
- [ ] Usage examples
- [ ] User documentation
- [ ] Integration with main docs

**Total Estimated Time**: 4-5 weeks

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Complex WSDL edge cases | Medium | Medium | Comprehensive testing with real WSDLs |
| Pydantic API changes | Low | Low | Pin Pydantic v2 dependency |
| User adoption concerns | Medium | Low | Excellent documentation + examples |
| Performance issues | Low | Low | Profile with large WSDLs |

---

## Part 7: Conclusion & Recommendations

### Conclusion

The research demonstrates that **Pydantic model generation from WSDL types is fully feasible** using Zeep's existing infrastructure. The implementation can be achieved through:

1. **Additive changes only** - No modifications to core Zeep
2. **Clean module structure** - New `zeep.codegen` module
3. **Reusing existing APIs** - Leveraging `zeep.xsd` introspection
4. **Well-defined scope** - ComplexTypes + SimpleTypes, no inheritance

### Recommendations

1. ✅ **Proceed with Implementation** - All technical requirements are met
2. ✅ **Start with Core Generator** - Focus on basic type mapping first
3. ✅ **Add Pydantic as Optional Dependency** - Keep zeep core lightweight
4. ✅ **Provide Both APIs** - Programmatic + CLI for different use cases
5. ✅ **Comprehensive Testing** - Test with diverse real-world WSDLs

### Next Steps

1. **User Approval**: Present this research for feedback
2. **Dependency Decision**: Confirm Pydantic v2 as optional dependency
3. **Implementation**: Begin Phase 1 (Core Generator)
4. **Iteration**: Regular feedback during implementation

---

## Appendices

### A. Complete Type Mapping Reference

| XSD Type | Python Type | Pydantic Field |
|----------|-------------|----------------|
| xs:string | str | `name: str` |
| xs:boolean | bool | `flag: bool` |
| xs:int | int | `count: int` |
| xs:long | int | `id: int` |
| xs:short | int | `code: int` |
| xs:byte | int | `byte: int` |
| xs:integer | int | `number: int` |
| xs:decimal | Decimal/float | `price: Decimal` |
| xs:float | float | `value: float` |
| xs:double | float | `value: float` |
| xs:date | date | `date: date` |
| xs:time | time | `time: time` |
| xs:dateTime | datetime | `timestamp: datetime` |
| xs:duration | timedelta | `duration: timedelta` |
| xs:base64Binary | bytes | `data: bytes` |
| xs:hexBinary | bytes | `data: bytes` |
| xs:anyURI | str | `url: str` |

### B. Zeep Code References

Key files to examine:
- `src/zeep/xsd/schema.py` - Type registry
- `src/zeep/xsd/types/complex.py` - ComplexType implementation
- `src/zeep/xsd/types/simple.py` - SimpleType implementation  
- `src/zeep/xsd/elements/element.py` - Element implementation
- `src/zeep/wsdl/definitions.py` - Operation definitions
- `src/zeep/xsd/printer.py` - Example of type introspection

### C. Related Projects

- **datamodel-code-generator**: Generates Pydantic models from JSON Schema/OpenAPI
- **xsdata**: Generates Python dataclasses from XSD (similar but different approach)
- **generateDS**: Older tool for XML bindings (not Pydantic)

Our approach is unique in being:
- Integrated with Zeep's existing WSDL client
- Focused on SOAP use cases (not general XSD)
- Providing both programmatic and interactive interfaces
