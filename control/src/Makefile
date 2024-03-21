CC       = g++
CMPFLAGS = -g -pthread
BSTFLAGS = -lboost_program_options -lboost_thread -lboost_atomic -lboost_date_time
UHDFLAGS = -luhd

all: clean format test radar

radar: radar.cpp recv.cpp
	$(CC) -o radar radar.cpp recv.cpp $(BSTFLAGS) $(UHDFLAGS) $(CMPFLAGS)
test: test.cpp recv.cpp
	$(CC) -o test test.cpp recv.cpp $(BSTFLAGS) $(CMPFLAGS)
format:
	clang-format --style=Google -i radar.cpp recv.cpp recv.h TSQueue.h test.cpp
clean:
	rm -f radar test
