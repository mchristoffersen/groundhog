CC       = g++
CMPFLAGS = -g
BSTFLAGS = -lboost_program_options -lboost_thread -lboost_atomic
UHDFLAGS = -luhd
OBJFILES = groundhog.o
TARGET   = ./radar

all: groundhog

groundhog:
	$(CC) -o $(TARGET) groundhog.cpp $(BSTFLAGS) $(UHDFLAGS) $(CMPFLAGS)
#all: $(TARGET)

#$(TARGET): $(OBJFILES)
#	$(CC) -o $@ $^ $(BSTFLAGS) $(UHDFLAGS) $(CMPFLAGS)

#%.o: %.cpp %.h
#	$(CC) -o $@ $< -c $(CMPFLAGS)

#clean:
#	rm -f $(OBJFILES) $(TARGET)
