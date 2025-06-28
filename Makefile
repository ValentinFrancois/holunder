requirements:
	pip install --upgrade pip && \
	pip install -e . && pip uninstall -y holunder && rm -rf holunder.egg*


requirements_dev:
	pip install -r requirements_dev.txt


lint:
	ruff check holunder/ test/


format:
	ruff format holunder/ test/ ; ruff check --fix holunder/ test/


tests:
	python3 -m pytest test/