PREFIX=/data/socorro
VIRTUALENV=$(CURDIR)/socorro-virtualenv
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s --with-xunit
COVEROPTS = --cover-html --cover-html-dir=html --with-coverage --cover-package=socorro
COVERAGE = $(VIRTUALENV)/bin/coverage
PYLINT = $(VIRTUALENV)/bin/pylint
PYTHONPATH = ".:thirdparty"
DEPS = nose psycopg2 simplejson coverage web.py pylint

.PHONY: all build install stage coverage hudson-coverage lint test

all:	test

test: virtualenv
	cd webapp-php/tests; phpunit *.php
	cd socorro/unittest/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done
	$(NOSE)

install:
	mkdir -p $(PREFIX)/htdocs
	mkdir -p $(PREFIX)/application
	rsync -a --exclude=".svn" thirdparty $(PREFIX)
	rsync -a --exclude=".svn" socorro $(PREFIX)/application
	rsync -a --exclude=".svn" scripts $(PREFIX)/application
	rsync -a --exclude=".svn" tools $(PREFIX)/application
	rsync -a --exclude=".svn" sql $(PREFIX)/application
	rsync -a --exclude=".svn" --exclude="tests" webapp-php/ $(PREFIX)/htdocs
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done
	cd $(PREFIX)/htdocs/modules/auth/config/; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/modules/recaptcha/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/application/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done

virtualenv:
	virtualenv $(VIRTUALENV)
	$(VIRTUALENV)/bin/easy_install $(DEPS)

coverage: virtualenv
	rm -rf html
	$(NOSE) $(COVEROPTS)

hudson-coverage: virtualenv
	rm -f coverage.xml
	$(COVERAGE) run $(NOSE); $(COVERAGE) xml

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;