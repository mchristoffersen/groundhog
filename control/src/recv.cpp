#include "recv.h"

#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/thread/thread.hpp>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <iostream>
#include <atomic>
#include <mutex>
#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <uhd/convert.hpp>
#include <uhd/exception.hpp>
#include <uhd/types/time_spec.hpp>
#include <uhd/types/tune_request.hpp>
#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/utils/safe_main.hpp>
#include <uhd/utils/thread.hpp>

#include "tsQueue.h"

#define TIME_STR_LEN 26
#define MAGIC0 0xD0D0BEEF
#define MAGIC1 0xFEEDFACE
#define MAGIC2 0xDEADDEAD

// Communication with scheduler
std::mutex t0_mutex;
std::atomic<bool> t0_valid(false);
uhd::time_spec_t t0;
std::atomic<double> nudge(0.0);

// buffer pointer
std::complex<short> *rx_buff;

size_t ampTriggerSingle(std::complex<short> *buff, size_t buff_len,
                        short trigger)
{
  /* Return location of first sample over a threshold value in an array.
   *
   * Inputs:
   *  buff - array of samples
   *  trigger - amplitude trigger threshold
   *
   * Returns:
   *  trigger index
   */
  // Loop over buffer and report trigger
  for (size_t i = 0; i < buff_len; i++)
  {
    if (std::abs(buff[i].real()) > trigger)
    {
      return i;
    }
  }
  return buff_len;
}

int acquireTrigger(size_t rate, size_t prf, uhd::rx_streamer::sptr rx_stream, short trigger, uhd::time_spec_t *t0)
{
  uhd::rx_metadata_t md;

  // Get initial PRF time basis
  double t = 1.2 / prf; // length of time to record (120% of PRF)
  uhd::stream_cmd_t t0_stream_cmd(
      uhd::stream_cmd_t::STREAM_MODE_NUM_SAMPS_AND_DONE);
  t0_stream_cmd.num_samps = size_t(rate * t);
  t0_stream_cmd.stream_now = true;

  // Complex buffer for received samples
  std::complex<short> *t0_buff = (std::complex<short> *)malloc(
      sizeof(std::complex<short>) * t0_stream_cmd.num_samps);

  // Stream samples
  rx_stream->issue_stream_cmd(t0_stream_cmd);
  size_t num_recvd_samps =
      rx_stream->recv(t0_buff, t0_stream_cmd.num_samps, md, 1);

  if (num_recvd_samps != t0_stream_cmd.num_samps)
  {
    std::cout
        << "Failed to record correct number of samples when acquiring trigger."
        << std::endl
        << boost::format("Requested: %d") % (t0_stream_cmd.num_samps)
        << std::endl
        << boost::format("Received:  %d") % (num_recvd_samps);
    return ~0;
  }

  // Find trigger time
  size_t trigSamp = ampTriggerSingle(t0_buff, t0_stream_cmd.num_samps, trigger);
  if (trigSamp == t0_stream_cmd.num_samps)
  {
    std::cout << "Failed to trigger when acquiring trigger." << std::endl;
    return ~0;
  }

  *t0 = md.time_spec + double(trigSamp) / rate; // time spec of trigger

  // free rx buffer for prf
  free(t0_buff);

  return 0;
}

int writeFileHeader(std::ofstream &fd, size_t spt, size_t pretrig, size_t prf,
                    size_t stack, short trigger, double rate)
{
  /* Write data file header.
   *
   * Inputs:
   *  fd - file stream to write to
   *  spt - samples per trace
   *  pretrig - pre-trigger samples
   *  prf - pulse repetition frequency
   *  stack - number of traces to stack
   *  trigger - amplitude trigger threshold
   *  rate - sampling frequency
   *
   * Returns:
   *  0 on success, non-zero on failure
   */

  // Write header
  uint64_t spt_file = uint64_t(spt);
  uint64_t pretrig_file = uint64_t(pretrig);
  uint64_t prf_file = uint64_t(prf);
  uint64_t stack_file = uint64_t(stack);

  fd.write((char *)&spt_file, sizeof(uint64_t));
  fd.write((char *)&pretrig_file, sizeof(uint64_t));
  fd.write((char *)&prf_file, sizeof(uint64_t));
  fd.write((char *)&stack_file, sizeof(uint64_t));
  fd.write((char *)&trigger, sizeof(short));
  fd.write((char *)&rate, sizeof(double));

  return 0;
}

int receive(uhd::usrp::multi_usrp::sptr usrp, uhd::rx_streamer::sptr rx_stream, RadarParams params, std::string file)
{
  // Unpack params
  size_t prf = params.prf;
  size_t spt = params.spt;
  size_t spb = params.spb;
  size_t pretrig = params.pretrig;
  size_t stack = params.stack;
  short trigger = params.trigger;
  double rate = params.rate;

  // Set up ZMQ socket
  zmq::context_t ctx(1);
  zmq::socket_t radarSock(ctx, zmq::socket_type::pub);
  radarSock.bind("tcp://localhost:5557");
  std::ostringstream msg;
  std::string msg_str;

  // Set up data file
  // Open file and write file signature
  std::ofstream fd;
  fd.open(file, std::ios::out | std::ios::binary);

  if (!fd.good())
  {
    std::cerr << "Error opening file for writing " << file << std::endl;
    return -1;
  }

  int magic0 = MAGIC0;
  fd.write((char *)&magic0, 4);

  // Write header
  uint64_t spt_file = uint64_t(spt);
  uint64_t pretrig_file = uint64_t(pretrig);
  uint64_t prf_file = uint64_t(prf);
  uint64_t stack_file = uint64_t(stack);

  writeFileHeader(fd, spt_file, pretrig_file, prf_file, stack_file, trigger, rate);

  if (!fd.good())
  {
    std::cerr << "Error writing file header to " << file << std::endl;
    return -1;
  }

  int magic1 = MAGIC1;
  fd.write((char *)&magic1, 4);

  // Container for time string
  std::string tmstr;
  boost::posix_time::ptime t;

  // Trace stacking buffer
  int64_t *trace = (int64_t *)calloc(spt, sizeof(int64_t));

  // Stacking and raw trace tracker
  size_t stacktrack = 0;
  size_t rcount = 0;

  // Variables for later
  size_t ntrace = 0;
  size_t trigSamp = 0;

  // Acquire trigger, need mutex on t0
  int acqStatus;
  {
    std::lock_guard<std::mutex> lock(t0_mutex);
    acqStatus = acquireTrigger(rate, prf, rx_stream, trigger, &t0);
  }
  if (acqStatus == ~0)
  {
    std::cout << "Failed to acquire trigger." << std::endl;
    return ~0;
  }
  else
  {
    // Got a t0!
    t0_valid.store(true);
  }
  // Complex buffer for received samples
  std::complex<short> *rx_buff = (std::complex<short> *)malloc(
      sizeof(std::complex<short>) * spb);
  size_t num_recvd_samps;
  uhd::rx_metadata_t md;

  uhd::time_spec_t lastTr = t0;
  while (true)
  {
    num_recvd_samps = rx_stream->recv(rx_buff, spb, md, 1);
    // std::cout << "rx time: " << md.time_spec.get_real_secs() << std::endl;

    // Catch timeout and see if thread has been interrupted
    if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_TIMEOUT)
    {
      std::cout << "Timeout in receive" << std::endl;
      try
      {
        boost::this_thread::sleep(boost::posix_time::milliseconds(10));
      }
      catch (boost::thread_interrupted &)
      {
        break;
      }
    }

    if (md.error_code != uhd::rx_metadata_t::ERROR_CODE_NONE && md.error_code != uhd::rx_metadata_t::ERROR_CODE_TIMEOUT)
    {
      std::cout << "Recieve error:" << std::endl
                << md.strerror() << std::endl;
      return ~0;
    }

    if (num_recvd_samps != spb)
    {
      std::cout
          << "Received incorrect number of samples in receive."
          << std::endl
          << boost::format("Requested: %d") % (spb)
          << std::endl
          << boost::format("Received:  %d") % (num_recvd_samps)
          << std::endl;
      return ~0;
    }

    // Stack (or stack then save if stacked enough)
    trigSamp = ampTriggerSingle(rx_buff, spb, trigger);

    // Check for no trigger
    if (trigSamp == spb)
    {
      std::cout << "Failed to trigger in receive." << std::endl;
      return ~0;
    }

    // Add samples to trace buffer
    for (size_t i = 0; i < spt; i++)
    {
      trace[i] = trace[i] + rx_buff[trigSamp - pretrig + i].real();
    }

    // +1 to counters
    stacktrack++;
    rcount++;

    // Update nudge every 64 traces
    if (rcount % 64 == 0)
    {
      // Set nudge
      nudge.store((double(trigSamp) - (double(spt) / 2.0)) / rate);
    }

    // Save a trace
    if (stacktrack == stack)
    {

      // save timestamp
      t = boost::posix_time::microsec_clock::universal_time();
      tmstr = to_iso_extended_string(t);
      fd.write(&tmstr[0], tmstr.size());

      if (tmstr.size() != TIME_STR_LEN)
      {
        std::cout << "WARNING!! TIME STRING NOT " << TIME_STR_LEN
                  << " CHARACTERS!! Time string is " << tmstr.size()
                  << " characters" << std::endl;
      }

      // save trace
      fd.write((char *)trace, spt * sizeof(int64_t));

      // Send update to daemon
      // memcpy(msgs[0].data(), tmstr.data(), TIME_STR_LEN);
      // memcpy(msgs[1].data(), trace, spt * sizeof(int64_t));
      // zmq::send_multipart(sock, msgs);

      // force flush of i/o buffer (write to disk now!)
      std::flush(fd);

      std::cout << std::fixed;
      std::cout << std::setprecision(6);

      // Print status message to screen
      std::cout << "  " << tmstr << " -- " << "Traces: " << ntrace
                << "    trigSamp: " << trigSamp
                << "    tr diff: " << (md.time_spec - lastTr).get_real_secs()
                << "    usrp diff: " << (md.time_spec - usrp->get_time_now()).get_real_secs()
                << "    stacktrack: " << stacktrack
                << std::endl;
      //<< "        \r"
      //<< std::flush;

      lastTr = md.time_spec;
      stacktrack = 0; // reset counter
      ntrace++;

      // Send trace count
      msg.str("");
      msg.clear();
      msg << "radar=0,ntrace=" << ntrace << ",prf=" << prf << ",adc=" << rate;
      msg_str = msg.str();
      radarSock.send(zmq::message_t(msg_str.data(), msg_str.size()), zmq::send_flags::none);

      zmq::message_t traceMsg(spt * sizeof(int64_t) + 5);
      memcpy(traceMsg.data(), "trace", 5);
      memcpy(static_cast<char *>(traceMsg.data()) + 5, trace, spt * sizeof(int64_t));
      radarSock.send(traceMsg, zmq::send_flags::none);

      // reset trace
      for (size_t i = 0; i < spt; i++)
      {
        trace[i] = 0;
      }
    }
  }

  // Close out
  int magic2 = MAGIC2;
  fd.write((char *)&magic2, 4);
  fd.close();
  std::cout << std::endl
            << "Consumer dead" << std::endl;

  return 0;
}

size_t detectPRF(std::complex<short> *buff, size_t buff_len, short trigger,
                 size_t spt, double rate)
{
  /* Function to auto-detect the pulse repetition frequency. This is done by
   * detecting several triggers in an array of continious samples and
   * calculating the mean separation between the triggers.
   *
   * Inputs:
   *  buff - buffer of samples
   *  trigger - amplitude trigger threshold
   *  spt - samples per trace (this many samples are skipped after a trigger)
   *  rate - sampling rate
   *
   * Returns:
   *  detected pulse repetition frequency
   */
  size_t ntrig =
      10000; // Maximum number of trigger events to detect for auto-trigger calc
  std::vector<size_t> trig_samp(ntrig);
  size_t trig_count = 0;

  // Loop over buffer and do triggering
  size_t i = 0;
  while (i < buff_len)
  {
    if (std::abs(buff[i].real()) > trigger)
    {
      trig_samp[trig_count] = i;
      trig_count += 1;
      i += spt;
    }
    if (trig_count == ntrig)
    {
      break;
    }
    i += 1;
  }

  if (trig_count < 2)
  {
    std::cout << "Failed to trigger twice for PRF detection!" << std::endl;
    return 0;
  }

  // Calculate mean time difference between triggers
  double dt;
  for (size_t i = 0; i < (trig_count - 1); i++)
  {
    dt += trig_samp[i + 1] - trig_samp[i];
  }
  dt /= trig_count - 1;
  dt /= rate;

  size_t prf = 1.0 / dt;

  // Round to nearest thousand
  // if (prf % 1000 < 500) {
  //  prf = prf - (prf % 1000);
  //} else {
  //  prf = prf + (1000 - (prf % 1000));
  //}

  return prf;
}