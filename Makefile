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
	@rm -rf build dist docs/build
	@find . -type f \( -name '*~' -or -name '*.pyc'  \) -delete

docs: $(call print-help,docs,Builds all documentation)
	@cd docs; make clean html man text

deploy-docs: $(call print-help,deploy-docs,Deploy documentation to gh-pages)
	@cd docs; make clean html
	@ghp-import -p docs/build/html

release: $(call print-help,release,Make code release, deploy docs to gh-pages) clean
	@fullrelease

.PHONY: dev install uninstall clean docs
