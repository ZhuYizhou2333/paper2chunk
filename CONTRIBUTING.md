# Contributing to paper2chunk

Thank you for your interest in contributing to paper2chunk! This document provides guidelines for contributing to the project.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/ZhuYizhou2333/paper2chunk.git
cd paper2chunk
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .
pip install pytest pytest-cov
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=paper2chunk --cov-report=html

# Run specific test file
pytest tests/test_pdf_parser.py
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and modular

## Pull Request Process

1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit:
```bash
git add .
git commit -m "Add your descriptive commit message"
```

3. Push to your fork:
```bash
git push origin feature/your-feature-name
```

4. Open a Pull Request on GitHub

5. Ensure all tests pass and add new tests for new features

## Areas for Contribution

- **Enhanced PDF parsing**: Better handling of complex layouts
- **Additional output formats**: Support for more RAG frameworks
- **Vision model integration**: Full chart-to-text implementation
- **Performance optimization**: Faster processing for large documents
- **Documentation**: Tutorials, examples, and guides
- **Testing**: More comprehensive test coverage

## Questions?

Feel free to open an issue for any questions or suggestions!
