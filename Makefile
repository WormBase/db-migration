
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
	find . -type f \( -name '*~' -or -name '*.pyc'  \) -delete


top-level-docs: $(call print-help,top-level-docs,Builds the top-level documentation)
	cd docs; make clean html man text

dev-docs: $(call print-help,dev-docs,Builds the documentation for users)
	cd docs/dev; make clean html man text

user-docs: $(call print-help,user-docs,Builds the documentation for developers)
	cd docs/user; make clean html man text

admin-docs: $(call print-help,admin-docs,Builds the documentation for developers)
	cd docs/admin; make clean html man text

docs-all: top-level-docs dev-docs admin-docs user-docs

.PHONY: install uninstall clean dev-docs user-docs
