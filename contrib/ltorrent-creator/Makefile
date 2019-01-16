all: deps
	g++ main.cpp            -std=c++11    -o ltorrent-creator \
		-lboost_system -ltorrent-rasterbar -lpthread \
		-llog4cplus \
		-lm optionparser/optionparser.o \
			logger/logger.o

.PHONY: all clean deps depsclean

DEPS = optionparser logger

deps:
	for dir in $(DEPS); do \
	  $(MAKE) -C $$dir; \
	done

depsclean:
	for dir in $(DEPS); do \
	  $(MAKE) -C $$dir clean; \
	done

clean: depsclean
	rm -f ltorrent-creator
