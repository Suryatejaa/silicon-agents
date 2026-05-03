PYTHON ?= python3

.PHONY: test test-compile run

test:
	PYTHONPYCACHEPREFIX=/tmp/sa-pycache $(PYTHON) -m unittest discover -s tests -v

test-compile:
	PYTHONPYCACHEPREFIX=/tmp/sa-pycache $(PYTHON) -m compileall silicon_agents main.py cli tests

run:
	$(PYTHON) -m uvicorn main:app --reload

