VPATH=slice

SLICE_FILES:=$(wildcard slice/*.ice)
SLICE_OUT=python
SLICE_TARGETS=$(SLICE_FILES:%.ice=$(SLICE_OUT)/%_ice.py)

PY_CONFIG=python/icecap/config.py

all: $(PY_CONFIG) slice configs

$(PY_CONFIG):
	ln -s config_dev.py $@

# Creates slice generated python files and packages.
slice: $(SLICE_OUT) $(SLICE_TARGETS)

$(SLICE_OUT)/%_ice.py: %.ice
	slice2py $< --ice -Islice --output-dir $(SLICE_OUT)

configs: registry.cfg client.cfg

%.cfg: python/icecap/config.py
	python scripts/make_config.py $@ > $@
