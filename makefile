TEST_PATH=./tests

init:
	pip3 install -r requirements.txt

lint:
	flake8 --exclude=.tox

test: clean-pyc
	py.test --verbose --color=yes $(TEST_PATH)

run:
	python3 deconz2mqtt.py

.PHONY: init clean-pyc
