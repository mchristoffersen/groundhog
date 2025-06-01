#pragma once
#include <complex>
#include <cstddef>
#include <uhd/usrp/multi_usrp.hpp>

struct RadarParams
{
    size_t prf;
    size_t spt;
    size_t spb;
    size_t pretrig;
    size_t stack;
    short trigger;
    double rate;
};

size_t ampTriggerSingle(std::complex<short> *buff, size_t buff_len,
                        short trigger);

int triggerAndStack(size_t prf, size_t spt, size_t pretrig, size_t spb,
                    size_t stack, short trigger, double fs, std::string file,
                    bool gui);

int receive(uhd::usrp::multi_usrp::sptr usrp, RadarParams params, std::string file);

size_t detectPRF(std::complex<short> *buff, size_t buff_len, short trigger,
                 size_t spt, double rate);