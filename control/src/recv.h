#pragma once
#include <complex>
#include <cstddef>

#include "TSQueue.h"

// Queues for passing data from radio download thread to triggering/stacking
// thread
static TSQueue<std::complex<short> *> freeq;
static TSQueue<std::complex<short> *> fullq;

size_t ampTriggerSingle(std::complex<short> *buff, size_t buff_len,
                        short trigger);

int triggerAndStack(size_t prf, size_t spt, size_t pretrig, size_t spb,
                    size_t stack, short trigger, double fs, std::string file);

size_t detectPRF(std::complex<short> *buff, size_t buff_len, short trigger,
                 size_t spt, double rate);
