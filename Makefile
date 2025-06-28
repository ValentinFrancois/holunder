requirements:
	pip install -e . && pip uninstall -y holunder && rm -rf holunder.egg*


requirements_dev:
	pip install -r requirements_dev.txt


format:
	ruff format holunder/ test/ ; ruff check --fix holunder/ test/
