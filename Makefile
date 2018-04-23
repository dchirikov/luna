.PHONY: all rpm clean
all: rpm

rpm:
	/bin/bash rpm/build.sh

clean:
	rm -rf rpm/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

