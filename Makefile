VPATH=slice grid

SLICE_FILES:=$(wildcard slice/*.ice)
SLICE_OUT=python
SLICE_TARGETS=$(SLICE_FILES:slice/%.ice=$(SLICE_OUT)/%_ice.py)

all: slice configs

# Creates slice generated python files and packages.
slice: $(SLICE_TARGETS)

$(SLICE_OUT)/%_ice.py: %.ice
	slice2py $< --ice -Islice --output-dir $(SLICE_OUT)

configs: registry.cfg client.cfg

%.cfg: python/icecap/config.py
	mkdir -p grid
	python scripts/make_config.py $@ grid/$@

update:
	python scripts/grid_admin.py update
