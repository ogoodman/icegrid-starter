VPATH=slice grid

SLICE_FILES:=$(wildcard slice/*.ice)
SLICE_TARGETS=$(SLICE_FILES:slice/%.ice=python/%_ice.py)

all: slice icegridgui

# Creates slice generated python files and packages.
slice: $(SLICE_TARGETS)

python/%_ice.py: %.ice
	slice2py $< --ice -Islice --output-dir python

update:
	python admin/grid_admin.py update

html:
	make -C doc html

icegridgui: IceGridGUI-3.5.1.jar

IceGridGUI-3.5.1.jar:
	cp /usr/share/java/IceGridGUI-3.5.1.jar . || touch $@

test:
	cd python ; nosetests

PACKAGES:=$(wildcard python/*/__init__.py)
COVER_PACKAGES:=$(PACKAGES:python/%/__init__.py=--cover-package=%)

test-coverage:
	mkdir -p python/coverage
	cd python ; nosetests --with-coverage --cover-erase --cover-inclusive --cover-tests --cover-html --cover-html-dir=coverage $(COVER_PACKAGES)
