// Michael Christoffersen 2023
// Updated Feb 2025
// Groundhog radar receiver control software
// Real-mode streaming and triggering from Ettus N210

#include <sys/socket.h>

#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/thread/thread.hpp>
#include <csignal>
#include <cstdlib>
#include <execinfo.h>
#include <fstream>
#include <atomic>
#include <mutex>
#include <iostream>
#include <uhd/convert.hpp>
#include <uhd/exception.hpp>
#include <uhd/types/time_spec.hpp>
#include <uhd/types/tune_request.hpp>
#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/utils/safe_main.hpp>
#include <uhd/utils/thread.hpp>

#include "recv.h"
#include "tsQueue.h"

namespace po = boost::program_options;

// stop signal
static bool stop_signal_called = false;

// Define the function to be called when ctrl-c (SIGINT) or SIGTERM is sent to
// process
void sigint_sigterm_handler(int signum)
{
  std::cout << "\nStopping" << std::endl;
  stop_signal_called = true;
}

void segfault_handler(int sig)
{
  void *array[50];
  size_t size;

  // get void*'s for all entries on the stack
  size = backtrace(array, 50);

  // print out all the frames to stderr
  std::cerr << "\n*** Caught signal " << sig << " ***\n";
  backtrace_symbols_fd(array, size, STDERR_FILENO);

  std::cerr << "*** End of backtrace ***\n";

  std::_Exit(EXIT_FAILURE); // exit immediately
}

void dumpArrayTerminal(std::complex<short> *buff, size_t buff_len)
{
  std::cout << "[";
  for (int i = 0; i < buff_len; ++i)
  {
    std::cout << buff[i].real() << ",";
  }
  std::cout << "]" << std::endl;
}

void dumpArrayFile(std::complex<short> *buff, size_t buff_len,
                   std::string file_name)
{
  std::ofstream file(file_name, std::ios::out);
  for (size_t i = 0; i < buff_len - 1; ++i)
  {
    file << buff[i].real() << ",";
  }
  file << buff[buff_len - 1].real();
  file << std::endl;
}

int UHD_SAFE_MAIN(int argc, char *argv[])
{
  // set thread priority (high)
  uhd::set_thread_priority_safe(1, true);

  // signal handler
  std::signal(SIGINT, &sigint_sigterm_handler);
  std::signal(SIGTERM, &sigint_sigterm_handler);

  // Segfault handler
  std::signal(SIGSEGV, &segfault_handler); // handle segfault
  std::signal(SIGABRT, &segfault_handler); // handle abort()
  std::signal(SIGFPE, &segfault_handler);  // floating-point exception
  std::signal(SIGILL, &segfault_handler);  // illegal instruction
  std::signal(SIGBUS, &segfault_handler);  // bus error

  // variables to be set by po
  std::string file, args, subdev;
  size_t stack, spt, prf, pretrig;
  short trigger;
  double rate;
  bool gui = false;

  po::options_description desc("Allowed options");
  // clang-format off
  desc.add_options()
  ("help", "help message")
  ("file", po::value<std::string>(&file)->required(), "(required) output file name")
  ("rate", po::value<double>(&rate)->default_value(25e6, "25 MHz"), "set sampling rate (Hz)")
  ("stack", po::value<size_t>(&stack)->default_value(1000, "1k"), "set trace stacking")
  ("spt", po::value<size_t>(&spt)->default_value(512), "set samples per trace")
  ("pretrig", po::value<size_t>(&pretrig)->default_value(8), "set pre-trigger samples")
  ("trigger", po::value<short>(&trigger)->default_value(50, "50"), "set trigger threshold (counts)")
  ("prf", po::value<size_t>(&prf)->default_value(0, "auto-detect"), "pulse repetition frequency")
  ("gui", po::bool_switch(&gui), "communicate with gui")
  ("args", po::value<std::string>(&args)->default_value("addr=192.168.10.2,type=usrp2"), "(ADVANCED) multi uhd device address args")
  ("subdev", po::value<std::string>(&subdev)->default_value("A:A"), "(ADVANCED) subdevice specification");
  // clang-format on

  // Handle CLI
  po::variables_map vm;
  po::store(po::parse_command_line(argc, argv, desc), vm);

  // print the help message
  if (vm.count("help"))
  {
    std::cout << "Groundhog Radar Receiver " << desc << std::endl;
    std::cout << std::endl
              << "This application records impulse radar data "
                 "to a HDF5 file.\n"
              << std::endl;
    return ~0;
  }

  po::notify(vm);

  // N210 initialization variables
  double freq = 0;                        // No digital tuning
  std::vector<size_t> channel_list = {0}; // single channel, so hardcode channel 0
  double lo_offset = 0.0;                 // LFRF has no LO
  std::string ref = "internal";           // TODO: use GPSDO if available
  std::string cpu_format = "sc16";
  std::string wire_format = "sc16";

  // Create USRP device
  std::cout << std::endl;
  std::cout << "Creating the usrp device with: " << args << std::endl;
  uhd::usrp::multi_usrp::sptr usrp = uhd::usrp::multi_usrp::make(args);

  // Lock mboard clock
  if (vm.count("ref"))
  {
    usrp->set_clock_source(ref);
  }

  // always select the subdevice first, the channel mapping affects the other
  // settings
  if (vm.count("subdev"))
    usrp->set_rx_subdev_spec(subdev);

  // set the sample rate
  if (rate != 25e6 && rate != 50e6)
  {
    std::cerr << "Please specify a valid sample rate (25e6 or 50e6)" << std::endl;
    return ~0;
  }
  std::cout << boost::format("Setting RX Rate: %f Msps") % (rate / 1e6)
            << std::endl;
  usrp->set_rx_rate(rate, uhd::usrp::multi_usrp::ALL_CHANS);
  rate = usrp->get_rx_rate(channel_list[0]);
  std::cout
      << boost::format("Actual RX Rate: %f Msps") %
             (rate / 1e6)
      << std::endl
      << std::endl;

  // set the center frequency
  std::cout << boost::format("Setting RX Freq: %f MHz...") % (freq / 1e6)
            << std::endl;
  std::cout << boost::format("Setting RX LO Offset: %f MHz...") %
                   (lo_offset / 1e6)
            << std::endl;
  uhd::tune_request_t tune_request(freq, lo_offset);
  if (vm.count("int-n"))
    tune_request.args = uhd::device_addr_t("mode_n=integer");
  for (size_t chan : channel_list)
    usrp->set_rx_freq(tune_request, chan);
  std::cout << boost::format("Actual RX Freq: %f MHz...") %
                   (usrp->get_rx_freq(channel_list[0]) / 1e6)
            << std::endl
            << std::endl;

  // No gain
  // No IF filter
  // No antenna
  // No need to check ref and LO lock

  // For communication with receive thread
  extern std::mutex t0_mutex;
  extern std::atomic<bool> stream_valid;
  extern std::atomic<bool> t0_valid;
  extern uhd::time_spec_t t0;
  extern std::atomic<double> nudge;

  // Get 2 s of samples to auto-detect PRF
  // create a receive streamer
  uhd::stream_args_t stream_args(cpu_format, wire_format);
  stream_args.channels = channel_list;
  extern uhd::rx_streamer::sptr rx_stream;
  rx_stream = usrp->get_rx_stream(stream_args);
  stream_valid.store(true);

  uhd::rx_metadata_t md;

  // setup streaming
  double t = 2; // length of time to record (s)
  uhd::stream_cmd_t prf_stream_cmd(
      uhd::stream_cmd_t::STREAM_MODE_NUM_SAMPS_AND_DONE);
  prf_stream_cmd.num_samps = size_t(rate * t);
  prf_stream_cmd.stream_now = true;

  // Complex buffer for PRF detection
  std::complex<short> *prf_buff = (std::complex<short> *)malloc(
      sizeof(std::complex<short> *) * prf_stream_cmd.num_samps);

  // Stream samples
  rx_stream->issue_stream_cmd(prf_stream_cmd);
  size_t num_recvd_samps =
      rx_stream->recv(prf_buff, prf_stream_cmd.num_samps, md, .5);

  if (num_recvd_samps != prf_stream_cmd.num_samps)
  {
    std::cout
        << "Failed to record correct number of samples for PRF auto-detect"
        << std::endl
        << boost::format("Requested: %d") % (prf_stream_cmd.num_samps)
        << std::endl
        << boost::format("Received:  %d") % (num_recvd_samps);
    return ~0;
  }

  // Check for at least one trigger event
  if (ampTriggerSingle(prf_buff, prf_stream_cmd.num_samps, trigger) ==
      prf_stream_cmd.num_samps)
  {
    std::cout << "Failed to trigger!" << std::endl;
    return ~0;
  }

  // Detect PRF and compare to declared one if applicable
  size_t prf_meas =
      detectPRF(prf_buff, prf_stream_cmd.num_samps, trigger, spt, rate);
  if (prf_meas == 0)
  {
    std::cout << "Failed to measure PRF" << std::endl;
    if (prf == 0)
    {
      return ~0;
    }
  }
  std::cout << boost::format("Detected PRF: %d Hz") % prf_meas << std::endl;
  std::cout << boost::format("Declared PRF: %d Hz") % prf << std::endl;
  if (prf == 0)
  {
    std::cout << "Using detected PRF.\n"
              << std::endl;
    prf = prf_meas;
  }

  size_t spb = 2 * spt; // samples per buffer (2x samples per trace)
  // TODO: should do some math here with pre-trigger samples...

  // free rx buffer for prf
  free(prf_buff);

  // Print config
  std::cout << "Sampling frequency: " << rate / 1e6 << " MHz" << std::endl
            << "Samples per trace: " << spt << std::endl
            << "Pre-trigger samples: " << pretrig << std::endl
            << "Stacking: " << stack << std::endl
            << "Trigger amplitude: " << trigger << std::endl;

  // spin up receiver thread
  RadarParams params;
  params.prf = prf;
  params.spt = spt;
  params.spb = spb;
  params.pretrig = pretrig;
  params.stack = stack;
  params.trigger = trigger;
  params.rate = rate;

  boost::thread receiver(receive, usrp, params, file);

  // Wait for valid t0
  while (not t0_valid)
  {
    usleep(1000);
    if (stop_signal_called)
    {
      break;
    }
  }

  // Set up stream cmd for receiving samples
  uhd::stream_cmd_t stream_cmd(uhd::stream_cmd_t::STREAM_MODE_NUM_SAMPS_AND_DONE);
  stream_cmd.stream_now = false;
  // TODO: add more nuance here
  stream_cmd.num_samps = spb;

  {
    // Need mutex on t0
    std::lock_guard<std::mutex> lock(t0_mutex);
    // Start 500 pulse intervals in the future, shift by half trace length
    // for trigger wiggle room
    stream_cmd.time_spec = t0 + 500.0 / prf - (spt / rate) / 2;
  }

  // Check timing and keep issuing stream commands until stop signal called
  size_t cmdCount = 0;
  size_t queueDepth = 16; // schedule this many commands in advance
  double leadTime;
  // std::cout << std::fixed;
  // std::cout << std::setprecision(6);

  // Initial commands
  for (int i = 0; i < queueDepth; i++)
  {
    stream_cmd.time_spec += 1.0 / double(prf);
    rx_stream->issue_stream_cmd(stream_cmd);
  }

  while (not stop_signal_called)
  {
    // Check lead time, sleep for a prf if too far out
    leadTime = (stream_cmd.time_spec - usrp->get_time_now()).get_real_secs();

    if (leadTime > double(queueDepth) / double(prf))
    {
      // std::cout << "next sched time: " << stream_cmd.time_spec.get_real_secs() << std::endl;
      // std::cout << "usrp time: " << usrp->get_time_now().get_real_secs() << std::endl;
      usleep(1e6 / double(prf));
      continue;
    }

    // Check if stream still valid
    if (not stream_valid)
    {
      // Remake stream
      rx_stream = usrp->get_rx_stream(stream_args);
      stream_valid.store(true);

      // Wait for good t0
      while (not t0_valid)
      {
        usleep(1000);
        if (stop_signal_called)
        {
          break;
        }
      }

      // Issue new stream commands
      {
        // Need mutex on t0
        std::lock_guard<std::mutex> lock(t0_mutex);
        // Start 500 pulse intervals in the future, shift by half trace length
        // for trigger wiggle room
        stream_cmd.time_spec = t0 + 500.0 / prf - (spt / rate) / 2;
      }

      for (int i = 0; i < queueDepth; i++)
      {
        stream_cmd.time_spec += 1.0 / double(prf);
        rx_stream->issue_stream_cmd(stream_cmd);
      }

      continue;
    }

    stream_cmd.time_spec += 1.0 / double(prf);
    rx_stream->issue_stream_cmd(stream_cmd);

    cmdCount++;

    if (cmdCount % queueDepth == 0)
    {
      // Check nudge every queueDepth commands
      stream_cmd.time_spec += nudge.exchange(0.0);

      // std::cout << "Stream time spec: " << stream_cmd.time_spec.get_real_secs()
      //           << std::endl
      //           << "USRP time: " << usrp->get_time_now().get_real_secs() << std::endl
      //           << std::endl;
    }
  }

  // When done
  // Interrupt and join
  receiver.interrupt();
  receiver.join();

  return 0;
}
