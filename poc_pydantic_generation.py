#!/usr/bin/env python
"""
Proof of Concept: Generate Pydantic models from WSDL

This script demonstrates the feasibility of generating Pydantic models
from WSDL/XSD types using Zeep's existing type introspection capabilities.
"""

import sys
from lxml import etree
from zeep.xsd import Schema

# Import our proof-of-concept generator
sys.path.insert(0, '/home/runner/work/python-zeep/python-zeep/src')
from zeep.codegen import generate_pydantic_models


def demo_type_introspection():
    """Demo: Show Zeep's type introspection capabilities"""
    print("=" * 80)
    print("DEMO: Zeep Type Introspection Capabilities")
    print("=" * 80)
    
    # Create sample schema
    schema_content = """
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="http://example.com/test"
            xmlns:tns="http://example.com/test">
  
  <xsd:complexType name="Person">
    <xsd:sequence>
      <xsd:element name="name" type="xsd:string"/>
      <xsd:element name="age" type="xsd:int"/>
      <xsd:element name="email" type="xsd:string" minOccurs="0"/>
      <xsd:element name="tags" type="xsd:string" minOccurs="0" maxOccurs="unbounded"/>
    </xsd:sequence>
  </xsd:complexType>
  
  <xsd:complexType name="Address">
    <xsd:sequence>
      <xsd:element name="street" type="xsd:string"/>
      <xsd:element name="city" type="xsd:string"/>
      <xsd:element name="zipCode" type="xsd:string"/>
    </xsd:sequence>
  </xsd:complexType>
  
</xsd:schema>
"""
    
    schema_node = etree.fromstring(schema_content.strip())
    schema = Schema(schema_node)
    
    # Get the Person type
    person_type = schema.get_type('{http://example.com/test}Person')
    
    print(f"\nType Name: {person_type.name}")
    print(f"Qualified Name: {person_type.qname}")
    print(f"Is Global: {person_type.is_global}")
    print(f"\nElements:")
    
    for elem_name, element in person_type.elements:
        print(f"  - {elem_name}:")
        print(f"      Type: {element.type}")
        print(f"      Optional: {element.is_optional}")
        print(f"      Multiple: {element.accepts_multiple}")
        print(f"      Min/Max: {element.min_occurs}/{element.max_occurs}")
    
    print("\n✓ Successfully demonstrated type introspection!")
    return True


def demo_pydantic_generation():
    """Demo: Generate Pydantic models from schema"""
    print("\n" + "=" * 80)
    print("DEMO: Generate Pydantic Models from XSD Schema")
    print("=" * 80)
    
    # Create sample schema with multiple types
    schema_content = """
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="http://example.com/test"
            xmlns:tns="http://example.com/test">
  
  <xsd:complexType name="User">
    <xsd:sequence>
      <xsd:element name="id" type="xsd:int"/>
      <xsd:element name="username" type="xsd:string"/>
      <xsd:element name="email" type="xsd:string"/>
      <xsd:element name="firstName" type="xsd:string" minOccurs="0"/>
      <xsd:element name="lastName" type="xsd:string" minOccurs="0"/>
      <xsd:element name="isActive" type="xsd:boolean"/>
      <xsd:element name="roles" type="xsd:string" minOccurs="0" maxOccurs="unbounded"/>
    </xsd:sequence>
  </xsd:complexType>
  
  <xsd:complexType name="Address">
    <xsd:sequence>
      <xsd:element name="street" type="xsd:string"/>
      <xsd:element name="city" type="xsd:string"/>
      <xsd:element name="state" type="xsd:string" minOccurs="0"/>
      <xsd:element name="zipCode" type="xsd:string"/>
    </xsd:sequence>
  </xsd:complexType>
  
</xsd:schema>
"""
    
    from zeep.codegen.generator import PydanticModelGenerator
    
    schema_node = etree.fromstring(schema_content.strip())
    schema = Schema(schema_node)
    
    generator = PydanticModelGenerator(schema)
    
    try:
        code = generator.generate_all_models()
        print("\nGenerated Pydantic Models:")
        print("-" * 80)
        print(code)
        print("-" * 80)
        print("✓ Successfully generated Pydantic models!")
        
        # Verify code compiles
        try:
            exec(compile(code, '<generated>', 'exec'))
            print("✓ Generated code compiles successfully!")
        except ImportError:
            print("⚠ Skipping compilation check (pydantic not installed)")
            print("  Generated code structure is valid")
        except Exception as e:
            print(f"✗ Generated code has syntax errors: {e}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error generating models: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("PROOF OF CONCEPT: Pydantic Model Generation from WSDL")
    print("=" * 80)
    print("\nThis demonstrates that Zeep's type system provides all the necessary")
    print("information to generate Pydantic models programmatically.\n")
    
    results = []
    
    # Run demos
    results.append(demo_type_introspection())
    results.append(demo_pydantic_generation())
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if all(results):
        print("\n✓ ALL DEMOS PASSED!")
        print("\nConclusion:")
        print("  - Zeep's type system provides complete introspection")
        print("  - XSD ComplexTypes can be converted to Pydantic models")
        print("  - Element cardinality maps to Optional and List types")
        print("  - The approach is technically feasible")
        print("\nNext Steps:")
        print("  - Enhance generator with enum support")
        print("  - Add constraint extraction (min/max, pattern)")
        print("  - Handle circular dependencies with forward references")
        print("  - Build interactive CLI interface")
        print("  - Add support for nested ComplexTypes")
    else:
        print("\n✗ Some demos failed")
        print("Please review the error messages above")
    
    return all(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
