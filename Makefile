.PHONY: tox test lint coverage build

TOX ?= tox

tox:
	$(TOX) -q

test:
	$(TOX) -qe py

lint:
	$(TOX) -qe flake8

coverage:
	$(TOX) -qe coverage

build:
	$(TOX) -qe build


# The end.
