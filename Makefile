PKG := azanium
PYTHON ?= $(shell which python3)
PIP := ${PYTHON} -m pip
DIST_NAME ?= $(shell ${PYTHON} setup.py --fullname)

define print-help
	$(if $(need-help),$(warning $1 -- $2))
endef

need-help := $(filter help,$(MAKECMDGOALS))

help: ; @echo $(if $(need-help),,Type \'$(MAKE)$(dash-f) help\' to get help)

dev: $(call print-help,dev,installs the ${PKG} python package for development)
	@if ! test -d "${VIRTUAL_ENV}"; then \
		echo "ERROR: No virtualenv active"; \
		exit 1; fi
	${VIRTUAL_ENV}/bin/python3 -m pip install -e ".[dev]"

install: $(call print-help,install,installs the ${PKG} python package in user-space)
	${PYTHON} setup.py sdist 2> /dev/null
	${PIP} install --user "dist/${DIST_NAME}.tar.gz"

uninstall: $(call print-help,uninstall,un-installs the Python package)
	${PIP} uninstall -y "${PKG}"

clean: $(call print-help,clean,Cleans build artefacts)
	@rm -rf build dist
	@find . -type f \( -name '*~' -or -name '*.pyc'  \) -delete

dev-docs: $(call print-help,dev-docs,Builds the documentation for users)
	@cd docs/dev; make clean html man text

user-docs: $(call print-help,user-docs,Builds the documentation for developers)
	@cd docs/user; make clean html man text latexpdf

admin-docs: $(call print-help,admin-docs,Builds the documentation for admins)
	@cd docs/admin; make clean html man text

docs-all: $(call print-help,docs-all,Builds all documentation) dev-docs admin-docs user-docs

docs: $(call print-help,docs,Builds all documentation)
	@cd docs; make clean html man text


.PHONY: dev install uninstall clean admin-docs dev-docs docs-all user-docs docs
