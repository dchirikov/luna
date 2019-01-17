all: deps
	g++ main.cpp            -std=c++11    -o ltorrent-server \
		-lboost_system -ltorrent-rasterbar -lpthread \
		-llog4cplus \
		-lm \
			optionparser/optionparser.o \
			exceptions/exceptions.o \
			helpers/helpers.o \
			logger/logger.o \
			server/torrents.o \
			server/server.o

.PHONY: all clean deps depsclean

DEPS = optionparser exceptions helpers logger server

deps:
	for dir in $(DEPS); do \
	  $(MAKE) -C $$dir; \
	done

depsclean:
	for dir in $(DEPS); do \
	  $(MAKE) -C $$dir clean; \
	done

clean: depsclean
	rm -f ltorrent-server
