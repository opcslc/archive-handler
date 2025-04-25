# Testing Guide for Telegram Archive Explorer

## Overview
This document outlines testing standards, practices, and guidelines for the Telegram Archive Explorer project.

## Test Structure
- `tests/test_basic.py`: Basic functionality tests
- `tests/test_integration.py`: End-to-end workflow tests
- `tests/test_performance.py`: Performance and scalability tests
- `tests/test_security.py`: Security and encryption tests
- `tests/test_validation.py`: Data validation tests
- `tests/test_cli.py`: Command-line interface tests
- `tests/factories.py`: Test data generation utilities
- `tests/conftest.py`: Shared fixtures and test configuration

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_basic.py

# Run tests by marker
pytest -m integration
pytest -m performance
pytest -m security

# Run with coverage
pytest --cov=telegram_archive_explorer
```

### Using tox for Multiple Python Versions
```bash
# Run tests across all supported Python versions
tox

# Run specific environment
tox -e py39
tox -e lint
tox -e type
```

## Test Categories

### Unit Tests
- Write unit tests for all new functions and classes
- Use appropriate fixtures from `conftest.py`
- Mock external dependencies
- Test both success and error cases

### Integration Tests
- Test complete workflows
- Verify component interactions
- Use realistic test data from `factories.py`
- Test error recovery and retry mechanisms

### Performance Tests
- Use `@pytest.mark.performance` decorator
- Follow benchmark thresholds in `pytest.benchmark.ini`
- Test with large datasets
- Verify scalability requirements

### Security Tests
- Test encryption at rest
- Verify secure deletion
- Check access controls
- Test data protection measures

## Test Data
- Use `TestDataFactory` for generating test data
- Avoid hardcoding test values
- Create realistic test scenarios
- Consider edge cases and boundary conditions

## Code Quality
Pre-commit hooks enforce:
- Black formatting
- Flake8 linting
- Pylint checks
- MyPy type checking
- Automated tests

## Writing New Tests

### Test Structure
```python
@pytest.mark.category
def test_specific_feature():
    """Clear description of what is being tested"""
    # Arrange
    # Set up test conditions
    
    # Act
    # Perform the action being tested
    
    # Assert
    # Verify the results
```

### Best Practices
1. Each test should have a single responsibility
2. Use descriptive test names
3. Include docstrings explaining test purpose
4. Follow the Arrange-Act-Assert pattern
5. Clean up test resources properly
6. Use appropriate markers

## CI/CD Integration
GitHub Actions workflow:
- Runs on push and pull requests
- Tests multiple Python versions
- Performs code quality checks
- Generates coverage reports
- Runs performance benchmarks

## Performance Standards
Refer to `pytest.benchmark.ini` for:
- Operation time limits
- Acceptable performance thresholds
- Regression tolerances

## Security Testing Standards
- Test encryption key management
- Verify secure data handling
- Check access control mechanisms
- Validate secure deletion
- Test configuration security

## Troubleshooting
1. Check the test logs
2. Verify test environment
3. Use pytest -v for verbose output
4. Check recent changes
5. Review similar test failures

## Adding New Test Types
1. Create appropriate test file
2. Add fixtures to `conftest.py`
3. Update `pyproject.toml` if needed
4. Document new test category
5. Add CI pipeline updates if required

## Test Coverage
- Maintain minimum 80% coverage
- Focus on critical paths
- Document excluded paths
- Regular coverage reviews

## Review Process
Test changes require:
1. Passing CI pipeline
2. Meeting coverage requirements
3. Following style guidelines
4. Proper documentation
5. Performance verification

## Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [Tox Documentation](https://tox.wiki/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [GitHub Actions](https://docs.github.com/en/actions)
