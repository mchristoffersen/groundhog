CC       = g++
CMPFLAGS = -g -pthread
BSTFLAGS = -lboost_program_options -lboost_thread -lboost_atomic -lboost_date_time
UHDFLAGS = -luhd -L/opt/uhd/lib -I/opt/uhd/include
ZMQFLAGS = -lzmq

all: clean radar

radar: radar.cpp recv.cpp
	$(CC) -o radar radar.cpp recv.cpp $(BSTFLAGS) $(UHDFLAGS) $(ZMQFLAGS) $(CMPFLAGS) 
test: test.cpp recv.cpp tsQueue.h
	$(CC) -o test test.cpp recv.cpp $(BSTFLAGS) $(ZMQFLAGS) $(CMPFLAGS)
testQueue: test_tsQueue.cpp
	$(CC) -o test_tsQueue test_tsQueue.cpp $(BSTFLAGS) $(CMPFLAGS)
format:
#	clang-format --style=Google -i radar.cpp recv.cpp recv.h tsQueue.h test.cpp
clean:
	rm -f radar test
