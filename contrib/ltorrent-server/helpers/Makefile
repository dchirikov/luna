all:
	g++ helpers.cpp -std=c++11 -c -o helpers.o

tests: all
	g++ tests.cpp -std=c++11 -lm helpers.o -o tests

clean:
	rm -f *.o tests
