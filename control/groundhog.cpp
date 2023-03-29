// Michael Christoffersen 2023
// Groundhog radar receiver control software
// Real-mode streaming and triggering from Ettus N210

#include <iostream>
#include <vector>
#include <csignal>
#include <cstdlib>

#include "TSQueue.h"

#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/thread/thread.hpp>
//#include <boost/lockfree/spsc_queue.hpp>
#include <boost/circular_buffer.hpp>

#include <uhd/convert.hpp>
#include <uhd/exception.hpp>
#include <uhd/types/time_spec.hpp>
#include <uhd/types/tune_request.hpp>
#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/utils/safe_main.hpp>
#include <uhd/utils/thread.hpp>

namespace po = boost::program_options;

// Queue for passing data from radio download thread to triggering/stacking thread
// 4 GB of samples
//static boost::lockfree::spsc_queue<short, boost::lockfree::capacity<20000000>> queue;
static TSQueue<short> queue; 

// stop signal
static bool stop_signal_called = false;

// Define the function to be called when ctrl-c (SIGINT) is sent to process
void sigint_handler(int signum) {
   std::cout << "Caught signal " << signum << std::endl;
   stop_signal_called = true;
}

size_t ampTriggerSingleCB(boost::circular_buffer<short> cb, short trigger){
     /* Return location of first trigger in a circular buffer
     *
     * Inputs:
     *  buff - buffer of samples
     *  trigger - amplitude trigger threshold
     *
     * Returns:
     *  trigger index
    */

    // Loop over buffer and do triggering
    for (size_t i = 0; i < cb.size(); i++) {
        if(cb[i] > trigger) {
            return i;
        }
    }
    return cb.size();
}

// Trigger and save samples
int triggerAndSave(size_t prf, size_t spt, size_t stack, short trigger, double fs) {
    //return 0;

    size_t cb_capacity = size_t(2*(1/prf)*fs);
    // Initialize ring buffer
    boost::circular_buffer<short> cb(cb_capacity);

    // interruption flag
    bool interrupt = false;

    // Initially fill ring buffer
    for (int i=0; i<cb_capacity; i++) {
        cb.push_back(queue.pop());
    }

    // Triggering loop
    size_t trig_samp = 0;
    while(not interrupt) {
        // trigger
        trig_samp = ampTriggerSingleCB(cb, trigger);

        // do stuff... stack samples, get system time when saving trace, etc
        //std::cout << boost::format("Trig samp: %zu") % trig_samp << std::endl;

        // push back new samples
        // Everything through current trace + 90% of the way to next one
        // Initially fill ring buffer
        for (int i=0; i<(trig_samp + spt + size_t(.9*(1/prf)*fs)); i++) {
            cb.push_back(queue.pop());
        } 

        // See if thread has been interrupted
        try {
            boost::this_thread::interruption_point();
        } catch(boost::thread_interrupted) {
            interrupt = true;
        }     
    }

    // Close out

    return 0;
}

size_t ampTriggerSingle(short* buff, size_t buff_len, short trigger){
     /* Return location of first trigger in an array
     *
     * Inputs:
     *  buff - array of samples
     *  trigger - amplitude trigger threshold
     *
     * Returns:
     *  trigger index
    */

    // Loop over buffer and do triggering
    for (size_t i = 0; i < buff_len; i++) {
        if(buff[i] > trigger) {
            return i;
        }
    }
    return buff_len;
}

size_t detect_prf(short* buff, size_t buff_len, short trigger, size_t spt, double rate) {
    /* Function to auto-detect the pulse repetition frequency. This is done by
     * detecting several triggers in an array of continious samples and calculating
     * the mean separation between the triggers.
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
    size_t ntrig = 50; // Maximum number of trigger events to detect for auto-trigger calc
    std::vector<size_t> trig_samp(ntrig);
    size_t trig_count = 0;

    // Loop over buffer and do triggering
    for (size_t i = 0; i < buff_len; i++) {
        if(buff[i] > trigger) {
            trig_samp[trig_count] = i;
            trig_count += 1;
            i += spt;
        }
        if(trig_count == ntrig) {
            break;
        }
    }
    
    if(trig_count < 2) {
        std::cout << "Failed to trigger twice for PRF detection!" << std::endl;
        return 0;
    }

    // Calculate mean time difference between triggers
    double dt;
    for (size_t i = 0; i < trig_count-1; i++) {
        dt += trig_samp[i+1] - trig_samp[i];
    }
    std::cout << std::endl;
    dt /= trig_count;
    dt /= rate;

    size_t prf = 1.0/dt;

    // Round to nearest thousand - 
    std::cout << "Rounding PRF to nearest increment of 1000" << std::endl;

    if (prf % 1000 < 500) {
        prf = prf - (prf % 1000);
    } else {
        prf = prf + (1000 - (prf % 1000));
    }

    return prf;
}

int UHD_SAFE_MAIN(int argc, char* argv[]) {
    // set thread priority (high)
    uhd::set_thread_priority_safe();

    // signal handler
    std::signal(SIGINT, &sigint_handler);

    // variables to be set by po
    std::string outdir, args, subdev;
    size_t stack, spt, prf;
    short trigger;
    double rate;

    po::options_description desc("Allowed options");
    desc.add_options()
        ("help", "help message")
        ("rate", po::value<double>(&rate)->default_value(20e6, "20 MHz"), "set sampling rate (Hz)")
        ("stack", po::value<size_t>(&stack)->default_value(5000, "5k"), "set trace stacking")
        ("spt", po::value<size_t>(&spt)->default_value(512), "set samples per trace")
        ("trigger", po::value<short>(&trigger)->default_value(25, "25"), "set trigger threshold (counts)")
        ("prf", po::value<size_t>(&prf)->default_value(0, "auto-detect"), "pulse repetition frequency")
        ("outdir", po::value<std::string>(&outdir)->default_value("./"), "output directory")
        ("args", po::value<std::string>(&args)->default_value("addr=192.168.10.2,type=usrp2"), "(ADVANCED) multi uhd device address args")
        ("subdev", po::value<std::string>(&subdev)->default_value("A:A"), "(ADVANCED) subdevice specification")
    ; 

    // Handle CLI
    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, desc), vm);
    po::notify(vm);

    // Whether to print overflow message
    bool overflow_message = true;

    // Samples in receive buffer
    size_t spb = 10000;

    // Center freq must be zero
    double freq = 0;

    // This is a single channel application so hardcoding channel 0
    std::vector<size_t> channel_list = {0};

    // Using LFRX with no LO
    double lo_offset = 0.0;

    // Using internal clock
    std::string ref = "internal";

    // Hardcoding cpu and wire formats
    std::string cpu_format = "sc16";
    std::string wire_format = "sc16";

    // print the help message
    if (vm.count("help")) {
        std::cout << "Groundhog Radar Receiver " << desc << std::endl;
        std::cout << std::endl
                  << "This application records impulse radar data "
                     "to a file.\n"
                  << std::endl;
        return ~0;
    }

    // create a usrp device
    std::cout << std::endl;
    std::cout << "Creating the usrp device with: " << args << "..." << std::endl;
    uhd::usrp::multi_usrp::sptr usrp = uhd::usrp::multi_usrp::make(args);

    // Lock mboard clock
    if (vm.count("ref")) {
        usrp->set_clock_source(ref);
    }

    // always select the subdevice first, the channel mapping affects the other settings
    if (vm.count("subdev"))
        usrp->set_rx_subdev_spec(subdev);

    // set the sample rate
    if (rate <= 0.0) {
        std::cerr << "Please specify a valid sample rate" << std::endl;
        return ~0;
    }
    std::cout << boost::format("Setting RX Rate: %f Msps...") % (rate / 1e6) << std::endl;
    usrp->set_rx_rate(rate, uhd::usrp::multi_usrp::ALL_CHANS);
    std::cout << boost::format("Actual RX Rate: %f Msps...")
                     % (usrp->get_rx_rate(channel_list[0]) / 1e6)
              << std::endl
              << std::endl;


    // set the center frequency
    if (vm.count("freq")) { // with default of 0.0 this will always be true
        std::cout << boost::format("Setting RX Freq: %f MHz...") % (freq / 1e6)
                  << std::endl;
        std::cout << boost::format("Setting RX LO Offset: %f MHz...") % (lo_offset / 1e6)
                  << std::endl;
        uhd::tune_request_t tune_request(freq, lo_offset);
        if (vm.count("int-n"))
            tune_request.args = uhd::device_addr_t("mode_n=integer");
        for (size_t chan : channel_list)
            usrp->set_rx_freq(tune_request, chan);
        std::cout << boost::format("Actual RX Freq: %f MHz...")
                         % (usrp->get_rx_freq(channel_list[0]) / 1e6)
                  << std::endl
                  << std::endl;
    }
    // No gain
    // No IF filter
    // No antennas
    // No need to check ref and LO lock


    // Get 100 ms of samples to auto-detect PRF with
    // create a receive streamer
    uhd::stream_args_t stream_args(cpu_format, wire_format);
    stream_args.channels             = channel_list;
    uhd::rx_streamer::sptr rx_stream = usrp->get_rx_stream(stream_args);

    uhd::rx_metadata_t md;



    // setup streaming
    float t = 0.1; // length of time to record
    uhd::stream_cmd_t prf_stream_cmd(uhd::stream_cmd_t::STREAM_MODE_NUM_SAMPS_AND_DONE);
    prf_stream_cmd.num_samps  = size_t(usrp->get_rx_rate(channel_list[0]) * t);
    prf_stream_cmd.stream_now = true;

    // Complex buffer for PRF detection
    std::complex<short> prf_buff[prf_stream_cmd.num_samps];

    // Stream samples
    rx_stream->issue_stream_cmd(prf_stream_cmd);
    size_t num_recvd_samps = rx_stream->recv(prf_buff, prf_stream_cmd.num_samps, md, .5);
    
    if (num_recvd_samps != prf_stream_cmd.num_samps) {
        std::cout << "Failed to record correct number of samples for PRF auto-detect" 
                  << std::endl << boost::format("Requested: %d") % (prf_stream_cmd.num_samps)
                  << std::endl << boost::format("Received:  %d") % (num_recvd_samps);
        return ~0;
    }

    // Extract real values (imag should be zero since center freq is zero)
    short* prf_buff_real = (short*)malloc(sizeof(short)*prf_stream_cmd.num_samps);

    for (size_t i = 0; i < prf_stream_cmd.num_samps; i++) {
        prf_buff_real[i] = prf_buff[i].real();
    }

    // Check for at least one trigger event
    if(ampTriggerSingle(prf_buff_real, prf_stream_cmd.num_samps, trigger) == prf_stream_cmd.num_samps) {
        std::cout << "Failed to trigger!" << std::endl;
        return ~0;
    }

    // Detect PRF and compare to declared one if applicable
    size_t prf_meas = detect_prf(prf_buff_real, prf_stream_cmd.num_samps, trigger, spt, rate);
    if (prf_meas == 0) {
        std::cout << "Failed to measure PRF" << std::endl;
        if(prf == 0) {
            return ~0;
        }
    }
    std::cout << boost::format("Detected PRF: %d Hz") % prf_meas << std::endl;
    std::cout << boost::format("Declared PRF: %d Hz") % prf << std::endl;
    if(prf == 0) {
        std::cout << "Using detected PRF." << std::endl;
        prf = prf_meas;
    }

    // set up receive buffer (depends on spt and cpu_format)
    std::complex<short> rx_buff[spb];

    // spin up consumer thread
    boost::thread consumer(triggerAndSave, prf, spt, stack, trigger, rate);

    // Stream samples continuiously and send to consumer thread
    uhd::stream_cmd_t stream_cmd(uhd::stream_cmd_t::STREAM_MODE_START_CONTINUOUS);
    stream_cmd.stream_now = true;   
    rx_stream->issue_stream_cmd(stream_cmd);

    size_t count = 0;
    while (not stop_signal_called) {
        // Receive samples
        num_recvd_samps = rx_stream->recv(rx_buff, spb, md, .5);

        //std::cout << boost::format("Received samples %d") % count << std::endl;
        //count++;

        // Check that right number of samps were received
        if(num_recvd_samps != spb) {
            std::cout << "Bad number of recv samples, skipping queue push" << std::endl
                      << boost::format("Recieved: %zu") % num_recvd_samps << std::endl
                      << boost::format("Requested: %zu") % spb << std::endl;
            //break;
        }

        // Check for other issues
       if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_TIMEOUT) {
            std::cout << std::endl << "Timeout while streaming" << std::endl;
            break;
        }
        if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_OVERFLOW) {
            if (overflow_message) {
                overflow_message = false;
                std::cout << std::endl << "Overflow indication" << std::endl;
            }
            continue;
        }
        if (md.error_code != uhd::rx_metadata_t::ERROR_CODE_NONE) {
            std::string error = "Receiver error: " + md.strerror();
        }        

        // Push real part to queue
        for (size_t i = 0; i < num_recvd_samps; i++) {
            queue.push(rx_buff[i].real());
        }
    }

    // Stop streaming
    uhd::stream_cmd_t stream_cmd_stop(uhd::stream_cmd_t::STREAM_MODE_STOP_CONTINUOUS);
    rx_stream->issue_stream_cmd(stream_cmd_stop);

    // free rx buffer
    free(prf_buff_real);
    // Interrupt and join
    consumer.interrupt();
    consumer.join();

    std::cout << "Goodbye" << std::endl;

    return 0;
}
