# TOON_TO_JSON
A Comprehensive python repo for toon format and Json comparison

# Project Documentation

This project contains several Python scripts for processing 'toon' data, generating few-shot examples, and validating outputs using either local or LLM-based methods.

## Project Structure

- **generate_toon_few_shots.py**: Generates few-shot examples.
- **toon_to_json_llm_validation.py**: Validates toon data to JSON using an LLM.
- **toon_to_json_local_validation.py**: Validates toon data locally.
- **test.py**: Sample test script.
- **pyproject.toml** and **uv.lock**: Dependency definitions for the `uv` Python toolchain.
- **.gitignore**, **LICENSE**, existing **README.md**.

## Requirements

- Python 3.10+
- UV package manager (`pip install uv`)
- Dependencies installed via `uv sync`

## Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Shuaib11-Github/TOON_TO_JSON.git
   cd TOON_TO_JSON
   ```
2. Install `uv`:
   ```bash
   pip install uv
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```

# Set up .env first!
cp .env.example .env

## Usage

### Generating Few-Shot Examples
```bash
uv run generate_toon_few_shots.py
```

### Validating using LLM
```bash
uv run toon_to_json_llm_validation.py
```

### Validating Locally
```bash
uv run toon_to_json_local_validation.py
```

### Running Tests
```bash
uv run test.py
```

