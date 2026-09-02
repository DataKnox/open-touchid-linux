.PHONY: test probe

test:
	python3 -m compileall -q src tests
	python3 -m unittest discover -s tests -v

probe:
	python3 src/open_touchid_probe.py
