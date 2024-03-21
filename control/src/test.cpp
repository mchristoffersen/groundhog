// Michael Christoffersen 2024
// Test harness for non-UHD parts of radar control software

#include "recv.h"

int main() {
  // ampTriggerSingle test 1
  size_t trig;
  std::complex<short> x[4];
  x[0] = std::complex<short>(1, 0);
  x[1] = std::complex<short>(1, 0);
  x[2] = std::complex<short>(3, 0);
  x[3] = std::complex<short>(1, 0);
  trig = ampTriggerSingle(x, 4, 2);

  if(trig != 2) {
    std::cout << "ampTriggerSingle failed test 1" << std::endl;
    std::cout << "Expected trigger sample: 2" << std::endl;
    std::cout << "Returned trigger sample: " << trig << std::endl;
    return 1;
  }

  // detectPRF test 1
  size_t prf;
  std::complex<short> y[1000];
  for(int i=1; i<1000; i++) {
    if(!(i%100)) {
      y[i] = std::complex<short>(10, 0);
    } else {
      y[i] = std::complex<short>(0, 0);
    }
  }
  // Print out the elements of the array
  //for (int i = 0; i < 1000; ++i) {
   //   std::cout << "Element " << i << ": " << y[i].real() << " + " << y[i].imag() << "i" << std::endl;
  //}

  prf = detectPRF(y, 1000, 5, 50, 1000);

  if(prf != 10) {
    std::cout << "detectPRF failed test 1" << std::endl;
    std::cout << "Expected PRF: 10" << std::endl;
    std::cout << "Returned PRF: " << prf << std::endl;
    return 1;
  }
  return 0;
}