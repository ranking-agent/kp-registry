# KP Registry
List of all valid registered Knowledge Providers on Smart API

## Setup:
To install:
```bash
pip install kp-registry
```

KP Registry will also use an environment variable:
```
KP_TRAPI_VERSION=1.5.0
```

## Usage:
```python
from kp_registry import Registry

# Initialize the registry
registry = Registry()
# Fetch all valid kps from Smart API
registry.refresh()

# Search for a kp given the following arguments
registry.search(
  subject_category,
  predicate,
  object_category,
  maturity,
)
```

## Release
kp-registry is automatically uploaded to pypi. To make a new release, simply make a new release and tag in the repo.
