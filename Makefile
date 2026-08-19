.PHONY: load ratios test report dashboard api clean

load:
	python src/etl/loader.py

ratios:
	python src/etl/financial_ratios.py

test:
	pytest tests/

report:
	python src/report.py

dashboard:
	python src/dashboard.py

api:
	python src/api.py

clean:
	python -c "import os, shutil; [shutil.rmtree(p) for p in ['__pycache__'] if os.path.exists(p)]"