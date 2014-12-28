VPATH=slice grid

SLICE_FILES:=$(wildcard slice/*.ice)
SLICE_TARGETS=$(SLICE_FILES:slice/%.ice=python/%_ice.py)

all: slice

# Creates slice generated python files and packages.
slice: $(SLICE_TARGETS)

python/%_ice.py: %.ice
	slice2py $< --ice -Islice --output-dir python

update:
	python scripts/grid_admin.py update

test:
	cd python ; nosetests

test-coverage:
	mkdir -p python/coverage
	cd python ; nosetests --with-coverage --cover-erase --cover-inclusive --cover-tests --cover-package=icecap --cover-html --cover-html-dir=coverage

html:
	python scripts/make_doc_templates.py
	make -C doc html
