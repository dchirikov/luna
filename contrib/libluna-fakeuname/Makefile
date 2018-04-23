all :
	gcc -Wall -fPIC -g -c -DLINUX -Wall libluna-fakeuname.c
	gcc -shared -rdynamic -o libluna-fakeuname.so libluna-fakeuname.o -ldl

clean :
	rm -f libluna-fakeuname.so
	rm -f libluna-fakeuname.o

