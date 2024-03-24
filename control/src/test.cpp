// Michael Christoffersen 2024
// Test harness for non-UHD parts of radar control software
#include <boost/thread/thread.hpp>
#include <iostream>

#include "recv.h"
#include "tsQueue.h"

int main() {
  // ampTriggerSingle test 1
  size_t trig;
  std::complex<short> x[4];
  x[0] = std::complex<short>(1, 0);
  x[1] = std::complex<short>(1, 0);
  x[2] = std::complex<short>(3, 0);
  x[3] = std::complex<short>(1, 0);
  trig = ampTriggerSingle(x, 4, 2);

  if (trig != 2) {
    std::cout << "ampTriggerSingle failed test 1" << std::endl;
    std::cout << "Expected trigger sample: 2" << std::endl;
    std::cout << "Returned trigger sample: " << trig << std::endl;
    return 1;
  }
  std::cout << "ampTriggerSingle PASSED" << std::endl;

  // detectPRF test 1
  size_t prfDetect;
  std::complex<short> y[1000];
  for (size_t i = 1; i < 1000; i++) {
    if (!(i % 100)) {
      y[i] = std::complex<short>(10, 0);
    } else {
      y[i] = std::complex<short>(0, 0);
    }
  }

  prfDetect = detectPRF(y, 1000, 5, 50, 1000);

  if (prfDetect != 10) {
    std::cout << "detectPRF failed test 1" << std::endl;
    std::cout << "Expected PRF: 10" << std::endl;
    std::cout << "Returned PRF: " << prfDetect << std::endl;
    return 1;
  }
  std::cout << "detectPRF PASSED" << std::endl;

  // triggerAndStack test 1
  size_t prf = 1000;
  size_t spt = 512;
  size_t pretrig = 32;
  size_t spb = 10000;
  size_t stack = 10;
  short trigger = 5;
  double rate = 1e6;
  std::string file = "test.ghog";

  // Spin up consumer thread
  boost::thread consumer(triggerAndStack, prf, spt, pretrig, spb, stack,
                         trigger, rate, file);

  extern tsQueue<std::complex<short> *> freeq;
  extern tsQueue<std::complex<short> *> fullq;

  // Malloc a bunch of memory chunks for rx
  for (size_t i = 0; i < 100; i++) {
    freeq.push(
        (std::complex<short> *)malloc(sizeof(std::complex<short>) * spb));
  }

  // Make fake data and feed to consumer
  std::complex<short> *z;
  for (size_t i = 0; i < 500; i++) {
    z = freeq.pop();
    for (size_t j = 0; j < spb; j++) {
      if (!(j % 1000)) {    
        z[j] = std::complex<short>(2, 0);
        z[j+1] = std::complex<short>(10000, 0);
        j++;
      } else {
        z[j] = std::complex<short>(0, 0);
      }
    }
    usleep(10000);
    fullq.push(z);
  }

  // Interrupt and join
  consumer.interrupt();
  consumer.join();

  // free all memory chunks
  for (size_t i = 0; i < freeq.size(); i++) {
    free(freeq.pop());
  }
  for (size_t i = 0; i < fullq.size(); i++) {
    free(fullq.pop());
  }

  return 0;
}