.PHONY: setup pipeline pipeline-1 pipeline-2 pipeline-3 pipeline-4 pipeline-5 app clean

PYTHON = .venv/Scripts/python

# ── Setup ──────────────────────────────────────────────────────────────────────
setup:
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@if not exist .env copy .env.example .env && echo "Created .env from .env.example — add your OPENAQ_API_KEY"

# ── Pipeline ───────────────────────────────────────────────────────────────────
pipeline: pipeline-1 pipeline-2 pipeline-3 pipeline-4 pipeline-5

pipeline-1:
	@echo "==> Phase 1: Data Ingestion"
	$(PYTHON) src/ingestion/fetch_air_quality.py
	$(PYTHON) src/ingestion/fetch_weather.py
	$(PYTHON) src/ingestion/fetch_industrial.py
	$(PYTHON) src/ingestion/verify_data.py

pipeline-2:
	@echo "==> Phase 2: Data Cleaning"
	$(PYTHON) src/processing/clean_air_quality.py
	$(PYTHON) src/processing/clean_weather.py
	$(PYTHON) src/processing/clean_industrial.py
	$(PYTHON) src/processing/verify_cleaned.py

pipeline-3:
	@echo "==> Phase 3: Feature Engineering"
	$(PYTHON) src/features/build_features.py

pipeline-4:
	@echo "==> Phase 4: Model Training"
	$(PYTHON) src/models/baseline.py
	$(PYTHON) src/models/train_lgbm.py

pipeline-5:
	@echo "==> Phase 5: Evaluation + Interpretation"
	$(PYTHON) src/models/evaluate.py
	$(PYTHON) src/models/interpret.py

# ── App ────────────────────────────────────────────────────────────────────────
app:
	$(PYTHON) -m streamlit run app/main.py

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	@echo "Removing generated files..."
	rm -f data/cleaned/*.parquet
	rm -f data/features/*.parquet
	rm -f data/exports/*.csv
	rm -f data/predictions/*.parquet
	rm -f models/*.pkl
	rm -f reports/figures/*.png reports/figures/*.pdf
