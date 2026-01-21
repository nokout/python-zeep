# Pydantic Model Generation Research - Quick Start

This directory contains the completed research phase for adding Pydantic model generation capabilities to Zeep.

## 📋 Quick Links

- **[RESEARCH_SUMMARY.md](RESEARCH_SUMMARY.md)** - Executive summary (start here!)
- **[RESEARCH_PYDANTIC_CODEGEN.md](RESEARCH_PYDANTIC_CODEGEN.md)** - Full technical documentation
- **[poc_pydantic_generation.py](poc_pydantic_generation.py)** - Working proof of concept
- **[src/zeep/codegen/](src/zeep/codegen/)** - Prototype implementation

## ✅ Research Status: COMPLETE

All research objectives achieved:
- ✅ Zeep type system fully understood
- ✅ Implementation approach designed
- ✅ Technical feasibility confirmed
- ✅ Working proof-of-concept validated

## 🚀 Try the Proof of Concept

```bash
# Run the POC demonstration
python poc_pydantic_generation.py
```

**Output Example:**
```python
class User(BaseModel):
    """Pydantic model for User"""
    id: int
    username: str
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    isActive: bool
    roles: Optional[List[str]] = None
```

## 📊 Key Findings

### Technical Feasibility: ✅ CONFIRMED

The research demonstrates that:
1. **Zeep's type system** provides complete introspection capabilities
2. **No core modifications** needed - implementation is additive only
3. **Type mapping** is straightforward: XSD types → Python types → Pydantic models
4. **Prototype works** - successfully generates valid Pydantic code

### Proposed API

```python
from zeep import Client
from zeep.codegen import generate_pydantic_models

client = Client('http://example.com/service.wsdl')

# Generate all types
code = generate_pydantic_models(client, include_all_types=True)

# Generate for specific operation
code = generate_pydantic_models(client, operation_name='GetUser')

# Generate specific types
code = generate_pydantic_models(client, type_names=['User', 'Address'])
```

## 📁 File Guide

### Documentation
| File | Purpose | Size |
|------|---------|------|
| RESEARCH_SUMMARY.md | Executive summary for stakeholders | 9KB |
| RESEARCH_PYDANTIC_CODEGEN.md | Complete technical documentation | 27KB |
| README_RESEARCH.md | This file - quick start guide | 3KB |

### Implementation
| File | Purpose | Lines |
|------|---------|-------|
| src/zeep/codegen/__init__.py | Public API | 15 |
| src/zeep/codegen/generator.py | Core generation logic | 250+ |
| src/zeep/codegen/mapping.py | Type mapping utilities | 160+ |

### Validation
| File | Purpose | Output |
|------|---------|--------|
| poc_pydantic_generation.py | Proof of concept demo | ✅ ALL TESTS PASS |

## 🎯 Use Case Example

**Scenario**: User needs to fill in a SOAP request template

```python
# 1. Generate Pydantic models from WSDL
from zeep import Client
from zeep.codegen import generate_pydantic_model_classes

client = Client('user-service.wsdl')
models = generate_pydantic_model_classes(client)

# 2. Get the request model
CreateUserRequest = models['CreateUserRequest']

# 3. Fill template with IDE autocomplete and validation
request = CreateUserRequest(
    username='john_doe',
    email='john@example.com',
    firstName='John',
    lastName='Doe',
    password='secure123'
)

# 4. Validate and export to YAML
import yaml
print(yaml.dump(request.model_dump()))

# 5. Use with zeep client
response = client.service.CreateUser(**request.model_dump())
```

## 🏗️ Architecture Overview

```
WSDL Document
    ↓
Zeep Client (existing)
    ↓
Schema with XSD Types (existing)
    ↓
zeep.codegen.generator (NEW) ← Introspects types
    ↓
Pydantic Models (generated)
    ↓
User fills template → YAML → SOAP Request
```

## 📈 Implementation Roadmap

**Estimated Time**: 4-5 weeks

### Phase 1: Core Generator (1-2 weeks)
- [ ] Enhance type mapping
- [ ] Handle nested types
- [ ] Support all XSD built-ins

### Phase 2: Advanced Features (1 week)
- [ ] Enum generation
- [ ] Constraint extraction
- [ ] Circular reference handling

### Phase 3: API & CLI (1 week)
- [ ] Public API finalization
- [ ] CLI commands
- [ ] Integration tests

### Phase 4: Documentation (1 week)
- [ ] User guide
- [ ] API reference
- [ ] Examples

## 🤔 Open Questions for User

1. **Dependency Management**: Should Pydantic be optional or required?
   - Recommendation: Optional via `pip install zeep[codegen]`

2. **Enum Style**: Generate as Enum classes or Literal types?
   - Recommendation: Configurable, default to Literal

3. **Decimal Handling**: Use Decimal or float for xs:decimal?
   - Recommendation: Configurable, default to float

## ✨ Next Steps

1. **User Review**: Please review the documentation
2. **Feedback**: Provide any concerns or additional requirements
3. **Approval**: Confirm approach meets your needs
4. **Implementation**: Begin full implementation if approved

## 📞 Contact

For questions or feedback on this research, please:
- Review the issue/PR discussion
- Provide feedback on the research documents
- Suggest changes or improvements

---

**Research Phase**: ✅ COMPLETE  
**Status**: Awaiting user review and approval  
**Next**: Proceed to implementation or iterate based on feedback
