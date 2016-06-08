
define print-help
	$(if $(need-help),$(warning $1 -- $2))
endef

need-help := $(filter help,$(MAKECMDGOALS))

help: ; @echo $(if $(need-help),,Type \'$(MAKE)$(dash-f) help\' to get help)

install: $(call print-help,install,installs the Python package)
	python3 setup.py dist

uninstall: $(call print-help,uninstall,un-installs the Python package)
	python3 -m pip uninstall -y wormbase-db-build

clean: $(call print-help,clean,Cleans build artefacts)
	rm -rf build dist

docs: $(call print-help,docs,Builds the documentation for the Python package)
	cd docs; make clean html man text latextpdf

.PHONY: install uninstall clean docs
