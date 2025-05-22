# API End-to-End Tests

This directory contains end-to-end tests for the Smart Parking API using pytest.

## Test Structure

The tests are organized into the following files:

- `conftest.py` - Contains pytest fixtures used across multiple test files
- `test_user_registration.py` - Tests for the user registration API
- `test_user_authentication.py` - Tests for the user authentication API (login, token refresh)
- `test_user_profile.py` - Tests for the user profile API

## Running the Tests

To run all the tests:

```bash
python -m pytest
```

To run only the e2e tests:

```bash
python -m pytest -m e2e
```

To run tests with verbose output:

```bash
python -m pytest -v
```

To run a specific test file:

```bash
python -m pytest tests/test_user_registration.py
```

## Test Coverage

To generate a test coverage report:

```bash
python -m pytest --cov=src
```

## Test Database

The tests use a separate test database that is created and destroyed for each test session. This ensures that the tests don't interfere with your development database.

## Adding New Tests

When adding new tests:

1. Use the `@pytest.mark.django_db` decorator for tests that need database access
2. Use the `@pytest.mark.e2e` decorator for end-to-end tests
3. Use the fixtures defined in `conftest.py` for common setup
4. Follow the existing test patterns for consistency