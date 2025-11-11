.PHONY: install fmt lint test run clean

install:
	pip install -r requirements.txt

fmt:
	ruff check --fix .
	black .

lint:
	ruff check .
	mypy src

test:
	pytest -q

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

run:
	uvicorn src.api.server:app --reload --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

# Local development commands
# Note: MySQL should be running on your local machine
# Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB environment variables

migrate-sas:
	PYTHONPATH=. python scripts/migrate_sas_to_mysql_optimized.py \
		--input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data

# Create dummy clinical trial data (replaces SAS migration for now)
create-dummy-data:
	PYTHONPATH=. python scripts/create_dummy_clinical_trial_data.py

# Build PDF indices locally using Chroma vector DB
build-pdf-indices-local:
	PYTHONPATH=. python scripts/build_pdf_index_vector_db.py \
		--input-dir data/AllProvidedFiles_438 \
		--model text-embedding-3-small

# Reset vector DB (delete existing collection)
reset-vector-db:
	PYTHONPATH=. python scripts/build_pdf_index_vector_db.py \
		--input-dir data/AllProvidedFiles_438 \
		--model text-embedding-3-small \
		--reset

# Test local setup
test-local:
	python scripts/test_local_setup.py

# Run everything (API + Frontend)
run-all:
	./run_app.sh

# Run API only
run-api:
	./run_api_only.sh

