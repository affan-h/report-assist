cov:
	coverage run -m pytest
	coverage html

test:
	ENV=test pytest tests -s

# Default environment is local, override with: make run ENV=dev
ENV ?= local

run:
	poetry install && poetry run python3 main.py --env $(ENV) --debug
