all:
	g++ optionparser.cpp 	-std=c++11 -c -o optionparser.o
	g++ ltorrent-client.cpp -std=c++11 -c -o ltorrent-client.o
	g++ main.cpp            -std=c++11    -o ltorrent-client \
		-lboost_system -ltorrent-rasterbar -lpthread \
		-lm ltorrent-client.o optionparser.o

clean :
	rm -f ltorrent-client *.o
