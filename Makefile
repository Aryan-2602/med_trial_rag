.PHONY: install install-frontend fmt lint test run run-frontend clean build-index-pdf build-index-sas

install:
	pip install -r requirements.txt

install-frontend:
	pip install -r requirements-frontend.txt

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

run-frontend:
	streamlit run src/frontend/app.py --server.port 8501

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

build-index-pdf:
	python -m src.indexers.build_pdf_index \
		--input-dir data/AllProvidedFiles_438 \
		--bucket $(RAG_BUCKET) \
		--prefix rag/pdf_index \
		--manifest-key rag/manifest.json \
		--model text-embedding-3-small

build-index-sas:
	python -m src.indexers.build_sas_index \
		--input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
		--bucket $(RAG_BUCKET) \
		--prefix rag/sas_index \
		--manifest-key rag/manifest.json \
		--model text-embedding-3-small

