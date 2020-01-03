
init:
	pip3 install -r requirements.txt

lint:
	flake8 --exclude=.tox

test: clean-pyc
	python3 -m unittest -f tests/test_*.py

run:
	python3 main.py

.PHONY: init clean-pyc
