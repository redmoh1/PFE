# Tests Directory

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_api.py -v
pytest tests/test_ml_scripts.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=backend --cov=src --cov-report=html
```

### Run specific test class:
```bash
pytest tests/test_api.py::TestKPIEndpoints -v
```

### Run specific test function:
```bash
pytest tests/test_api.py::TestKPIEndpoints::test_kpis_without_dates -v
```

## Test Structure

- `test_api.py` - Backend API endpoint tests
- `test_ml_scripts.py` - ML scripts unit tests
- `conftest.py` - Pytest configuration and fixtures

## Requirements

Install test dependencies:
```bash
pip install pytest pytest-cov
```

## Current Coverage

**Backend API:** Basic tests for all endpoints  
**ML Scripts:** Data validation, calculations, sentiment  
**Target:** 70%+ code coverage
