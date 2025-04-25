# Contributing Guide

## Getting Started

### Development Environment Setup

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/telegram-archive-explorer.git
cd telegram-archive-explorer
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Development Dependencies**
```bash
pip install -e ".[dev]"
```

4. **Install Pre-commit Hooks**
```bash
pre-commit install
```

## Development Workflow

### Branch Naming Convention

- Features: `feature/description`
- Bugfixes: `fix/description`
- Documentation: `docs/description`
- Performance: `perf/description`
- Tests: `test/description`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

### Pull Request Process

1. **Create Feature Branch**
```bash
git checkout -b feature/new-feature
```

2. **Make Changes**
- Write code
- Add tests
- Update documentation

3. **Run Tests**
```bash
pytest
tox
```

4. **Submit PR**
- Fill PR template
- Link related issues
- Request reviews

## Code Standards

### Python Style Guide

1. **Code Formatting**
- Follow PEP 8
- Use Black formatter
- Max line length: 88
- Use type hints

2. **Example Code**
```python
from typing import List, Optional

class DataProcessor:
    """Process extracted data from archives.
    
    Attributes:
        batch_size: Number of items to process at once
        timeout: Maximum processing time in seconds
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        timeout: Optional[int] = None
    ) -> None:
        self.batch_size = batch_size
        self.timeout = timeout
    
    def process_batch(self, items: List[dict]) -> List[dict]:
        """Process a batch of items.
        
        Args:
            items: List of items to process
            
        Returns:
            List of processed items
            
        Raises:
            ProcessingError: If batch processing fails
        """
        try:
            return [self._process_item(item) for item in items]
        except Exception as e:
            raise ProcessingError(f"Batch processing failed: {e}")
```

### Documentation Standards

1. **Docstrings**
- Use Google style
- Include types
- Document exceptions
- Provide examples

2. **Comments**
- Explain complex logic
- Document assumptions
- Note limitations
- Reference issues/PRs

## Testing Requirements

### Test Categories

1. **Unit Tests**
```python
def test_data_processor():
    processor = DataProcessor(batch_size=10)
    items = [{"id": i} for i in range(10)]
    
    result = processor.process_batch(items)
    
    assert len(result) == 10
    assert all(isinstance(item, dict) for item in result)
```

2. **Integration Tests**
```python
@pytest.mark.integration
def test_end_to_end_processing():
    collector = DataCollector()
    processor = DataProcessor()
    storage = DataStorage()
    
    data = collector.collect()
    processed = processor.process_batch(data)
    result = storage.store(processed)
    
    assert result.status == "success"
```

3. **Performance Tests**
```python
@pytest.mark.performance
def test_processing_performance(benchmark):
    def process_large_batch():
        processor = DataProcessor(batch_size=1000)
        items = [{"id": i} for i in range(1000)]
        return processor.process_batch(items)
    
    result = benchmark(process_large_batch)
    assert len(result) == 1000
```

### Test Coverage

Requirements:
- Minimum 90% coverage
- All core functionality
- Error cases
- Edge cases

## Documentation

### Required Documentation

1. **Code Documentation**
- Module docstrings
- Class docstrings
- Function docstrings
- Complex logic

2. **Feature Documentation**
- User guide
- API reference
- Examples
- Configuration

3. **Change Documentation**
- Changelog entries
- Migration guides
- Breaking changes

## Review Process

### Code Review Checklist

1. **Code Quality**
- [ ] Follows style guide
- [ ] Properly documented
- [ ] Well-structured
- [ ] Efficient implementation

2. **Testing**
- [ ] Tests added/updated
- [ ] Coverage maintained
- [ ] Edge cases covered
- [ ] Performance verified

3. **Documentation**
- [ ] Docstrings complete
- [ ] README updated
- [ ] API docs current
- [ ] Examples provided

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

### Release Steps

1. **Prepare Release**
```bash
# Update version
bump2version minor

# Update changelog
git changelog -n v1.2.0

# Create release branch
git checkout -b release/1.2.0
```

2. **Quality Checks**
```bash
# Run full test suite
tox

# Build distribution
python -m build

# Check package
twine check dist/*
```

3. **Release**
```bash
# Tag release
git tag -a v1.2.0 -m "Release 1.2.0"

# Push to PyPI
twine upload dist/*
```

## Community

### Getting Help

- GitHub Issues
- Discussion Forums
- Stack Overflow
- Discord Channel

### Contributing Support

- Answer questions
- Review PRs
- Write documentation
- Report bugs

## See Also
- [Development Setup](setup.md)
- [Testing Guide](testing.md)
- [API Reference](api.md)
- [Security Guidelines](security.md)
