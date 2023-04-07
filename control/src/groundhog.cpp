// Michael Christoffersen 2023
// Groundhog radar receiver control software
// Real-mode streaming and triggering from Ettus N210

#include <iostream>
#include <fstream>
#include <csignal>
#include <cstdlib>

#include "TSQueue.h"

#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/thread/thread.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>

#include <uhd/convert.hpp>
#include <uhd/exception.hpp>
#include <uhd/types/time_spec.hpp>
#include <uhd/types/tune_request.hpp>
#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/utils/safe_main.hpp>
#include <uhd/utils/thread.hpp>

namespace po = boost::program_options;

// Queue for passing data from radio download thread to triggering/stacking thread
static TSQueue<std::complex<short>*> freeq;
static TSQueue<std::complex<short>*> fullq; 

// stop signal
static bool stop_signal_called = false;

// Define the function to be called when ctrl-c (SIGINT) is sent to process
void sigint_handler(int signum) {
   std::cout << "\nStopping" << std::endl;
   stop_signal_called = true;
}

size_t ampTriggerSingle(std::complex<short>* buff, size_t buff_len, short trigger){
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
        if(std::abs(buff[i].real()) > trigger) {
            return i;
        }
    }
    return buff_len;
}

// Trigger and save samples
int triggerAndStack(size_t prf, size_t spt, size_t pretrig, size_t spb, size_t stack, short trigger, double fs, std::string file) {
    // Make filename
    std::ofstream fd;
    fd.open(file, std::ios::out | std::ios::binary);
    int magic0 = 0xD0D0BEEF;
    fd.write((char*) &magic0, 4);
    
    // Write header
    uint64_t spt_file = uint64_t(spt);
    uint64_t pretrig_file = uint64_t(pretrig);
    uint64_t prf_file = uint64_t(prf);
    uint64_t stack_file = uint64_t(stack);
    
    fd.write((char*) &spt_file, sizeof(uint64_t));
    fd.write((char*) &pretrig_file, sizeof(uint64_t));
    fd.write((char*) &prf_file, sizeof(uint64_t));
    fd.write((char*) &stack_file, sizeof(uint64_t));
    fd.write((char*) &trigger, sizeof(short));    
    fd.write((char*) &fs, sizeof(double));            
    int magic1 = 0xFEEDFACE;
    fd.write((char*) &magic1, 4);
    
    // Buffer and for time string
    char tmstr[200];
    char* format = "%FT%T";
    
    // Trace stacking buffer (using float for this)
    int64_t* trace = (int64_t*)calloc(spt, sizeof(int64_t));
    
    // Stacking tracker
    size_t stacktrack = 0;
    
    // Number of samples to skip after trigger
    // 95% of the way to the next trigger
    size_t skipsamp = size_t(0.95*(fs/prf));
    size_t skipped = 0; // skipped sample counter for loop
    
    // buffer pointers for previous, current, next frame
    std::complex<short>* prv_buff;
    std::complex<short>* cur_buff;
    std::complex<short>* nxt_buff;

    // Get first three frames
    prv_buff = fullq.pop();
    cur_buff = fullq.pop();
    nxt_buff = fullq.pop();  
    
    // Detect first trigger, iterate through frames until one is found
    bool trig = false;
    size_t trigloc = 0;
    size_t sample_offset;
    size_t ntrace = 0;
    
    // Print file name
    std::cout << file << ":" << std::endl;
    while (not trig) {
        trigloc = ampTriggerSingle(cur_buff, spb, trigger);
        
        if (trigloc == spb) { // if no trigger detected
            // Check for death
            while(fullq.empty()) {
                // See if thread has been interrupted (and sleep for a bit if not)
                try {
                    boost::this_thread::sleep(boost::posix_time::milliseconds(1));
                } catch(boost::thread_interrupted&) {
                    goto CLOSE;
                }
            }
            freeq.push(prv_buff);
            prv_buff = cur_buff;
            cur_buff = nxt_buff;
            nxt_buff = fullq.pop();
            continue;
        }
        
        trig = true;
    }

    while (true) {
        // Stack (or stack then save if stacked enough)
        // Get pretrigger samples (check if need to use prv_buff)
        
        if(trigloc - pretrig < 0) {
            // If some pre-trigger samples are in previous buffer
            // look-behind
            for (size_t i=0; i<(pretrig-trigloc); i++) {
                trace[i] = trace[i] + prv_buff[spb - (pretrig-trigloc) + i].real();
            }
            
            // current buffer
            for (size_t i=0; i<trigloc; i++) {
                trace[i + (pretrig-trigloc)] = trace[i + (pretrig-trigloc)] + cur_buff[i].real();
            }
            
        } else {
            // If pre-trigger samples entirely within current buffer
            for (size_t i=0; i<pretrig; i++) {
                trace[i] = trace[i] + cur_buff[trigloc - pretrig + i].real();
            }
        }
        
        
        // Get trigger and post trigger samples (check if need to use nxt_buff)
        if(trigloc + (spt - pretrig) >= spb) {
            //If some post-trigger samples are in next buffer
            // current buffer
            for (size_t i=0; i<(spb - trigloc); i++) {
                trace[i + pretrig] = trace[i + pretrig] + cur_buff[i + trigloc].real();   
            }
            
            // look ahead
            for (size_t i=0; i<(spt - pretrig - (spb - trigloc)); i++) {
                trace[i + pretrig + (spb - trigloc)] = trace[i + pretrig + (spb - trigloc)] + nxt_buff[i].real();
            }
        } else {
            // Add post-trigger samples to trace
            for (size_t i=0; i<(spt-pretrig); i++) {
                trace[i + pretrig] = trace[i + pretrig] + cur_buff[i + trigloc].real();
            }
        }
        
        // +1 trace
        stacktrack++;

        // Save a trace
        if(stacktrack == stack) {
            // save timestamp
            time_t now = std::time(NULL);
            struct tm *tmp_now = std::localtime(&now);
            std::strftime(tmstr, sizeof(tmstr), format, tmp_now);
            fd.write(tmstr, std::strlen(tmstr));
            
            // save trace
            fd.write((char*)trace, spt*sizeof(int64_t));
            // reset trace
            for (size_t i=0; i<spt; i++) {
                trace[i] = 0;
            }
            stacktrack = 0;  // reset counter
            ntrace++;
            // Print status message to screen
            std::cout << "  " << tmstr << " -- "
                << "Traces: " << ntrace
                << "    Full Buff: " << fullq.size() 
                << "    Free Buff: " << freeq.size()
                << "        \r" << std::flush;
        }
        
        // Get next trigger
        // Skip frames
        //std::cout << "Skipping frames: " << std::floor((trigloc+skipsamp)/spb) << std::endl;
        for (size_t i=0; i<std::floor((trigloc+skipsamp)/spb); i++) {
            // Check if it is time to die
            while(fullq.empty()) {
                // See if thread has been interrupted (and sleep for a bit if not)
                try {
                    boost::this_thread::sleep(boost::posix_time::milliseconds(1));
                } catch(boost::thread_interrupted&) {
                    goto CLOSE;
                }
            }
            freeq.push(prv_buff);
            prv_buff = cur_buff;
            cur_buff = nxt_buff;
            nxt_buff = fullq.pop();
                    
        }
        
        // Look for trigger in remaining samples of current frame
        sample_offset = ((trigloc+skipsamp)%spb);
        trigloc = ampTriggerSingle(cur_buff + sample_offset, spb - sample_offset, trigger);
        trigloc = trigloc + sample_offset;
        
        if(trigloc == spb) { // if it is not present
            trig = false;
            do {
                // Check if dead
                while(fullq.empty()) {
                    // See if thread has been interrupted (and sleep for a bit if not)
                    try {
                        boost::this_thread::sleep(boost::posix_time::milliseconds(1));
                    } catch(boost::thread_interrupted&) {
                        goto CLOSE;
                    }
                }
                freeq.push(prv_buff);
                prv_buff = cur_buff;
                cur_buff = nxt_buff;
                nxt_buff = fullq.pop();
                
                trigloc = ampTriggerSingle(cur_buff, spb, trigger);
                
                if(trigloc == spb) {
                    continue;  
                }
                
                trig = true;
            } while (not trig);
        }
    }
    CLOSE:
    
    // Close out
    int magic2 = 0xDEADDEAD;
    fd.write((char*) &magic2, 4);
    fd.close();
    std::cout << "Consumer dead" << std::endl;
    return 0;
}

size_t detect_prf(std::complex<short>* buff, size_t buff_len, short trigger, size_t spt, double rate) {
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
        if(std::abs(buff[i].real()) > trigger) {
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

    if (prf % 1000 < 500) {
        prf = prf - (prf % 1000);
    } else {
        prf = prf + (1000 - (prf % 1000));
    }

    return prf;
}

int UHD_SAFE_MAIN(int argc, char* argv[]) {
    // set thread priority (high)
    uhd::set_thread_priority_safe(1, true);

    // signal handler
    std::signal(SIGINT, &sigint_handler);

    // variables to be set by po
    std::string file, args, subdev;
    size_t stack, spt, prf, pretrig;
    short trigger;
    double rate;

    po::options_description desc("Allowed options");
    desc.add_options()
        ("help", "help message")
        ("file", po::value<std::string>(&file)->required(), "(required) output file name")
        ("rate", po::value<double>(&rate)->default_value(20e6, "20 MHz"), "set sampling rate (Hz)")
        ("stack", po::value<size_t>(&stack)->default_value(5000, "5k"), "set trace stacking")
        ("spt", po::value<size_t>(&spt)->default_value(512), "set samples per trace")
        ("pretrig", po::value<size_t>(&pretrig)->default_value(8), "set pre-trigger samples")
        ("trigger", po::value<short>(&trigger)->default_value(50, "50"), "set trigger threshold (counts)")
        ("prf", po::value<size_t>(&prf)->default_value(0, "auto-detect"), "pulse repetition frequency")
        ("args", po::value<std::string>(&args)->default_value("addr=192.168.10.2,type=usrp2"), "(ADVANCED) multi uhd device address args")
        ("subdev", po::value<std::string>(&subdev)->default_value("A:A"), "(ADVANCED) subdevice specification")
    ; 

    // Handle CLI
    po::variables_map vm; 
    po::store(po::parse_command_line(argc, argv, desc), vm);
    
    // print the help message
    if (vm.count("help")) {
        std::cout << "Groundhog Radar Receiver " << desc << std::endl;
        std::cout << std::endl
                  << "This application records impulse radar data "
                     "to a file.\n"
                  << std::endl;
        return ~0;
    }
    
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
    std::complex<short>* prf_buff = (std::complex<short>*)malloc(sizeof(std::complex<short>*)*prf_stream_cmd.num_samps);

    // Stream samples
    rx_stream->issue_stream_cmd(prf_stream_cmd);
    size_t num_recvd_samps = rx_stream->recv(prf_buff, prf_stream_cmd.num_samps, md, .5);
    
    if (num_recvd_samps != prf_stream_cmd.num_samps) {
        std::cout << "Failed to record correct number of samples for PRF auto-detect" 
                  << std::endl << boost::format("Requested: %d") % (prf_stream_cmd.num_samps)
                  << std::endl << boost::format("Received:  %d") % (num_recvd_samps);
        return ~0;
    }

    // Check for at least one trigger event
    if(ampTriggerSingle(prf_buff, prf_stream_cmd.num_samps, trigger) == prf_stream_cmd.num_samps) {
        std::cout << "Failed to trigger!" << std::endl;
        return ~0;
    }

    // Detect PRF and compare to declared one if applicable
    size_t prf_meas = detect_prf(prf_buff, prf_stream_cmd.num_samps, trigger, spt, rate);
    if (prf_meas == 0) {
        std::cout << "Failed to measure PRF" << std::endl;
        if(prf == 0) {
            return ~0;
        }
    }
    std::cout << boost::format("Detected PRF: %d Hz") % prf_meas << std::endl;
    std::cout << boost::format("Declared PRF: %d Hz") % prf << std::endl;
    if(prf == 0) {
        std::cout << "Using detected PRF.\n" << std::endl;
        prf = prf_meas;
    }

    // free rx buffer for prf 
    free(prf_buff);

    // Print config
    std::cout << "Sampling frequency: " << rate
    	<< std::endl << "Samples per trace: " << spt
    	<< std::endl << "Pre-trigger samples: " << pretrig
    	<< std::endl << "Stacking: " << stack
    	<< std::endl << "Trigger amplitude: " << trigger << std::endl;
    	
    // spin up consumer thread
    boost::thread consumer(triggerAndStack, prf, spt, pretrig, spb, stack, trigger, rate, file);

    // Malloc a bunch of memory chunks for rx
    for (size_t i=0; i<2000; i++) {
        freeq.push((std::complex<short>*)malloc(sizeof(std::complex<short>)*spb));
    }
    
    // rx buffer pointer
    std::complex<short>* rx_buff;

    // Stream samples continuiously and send to consumer thread
    uhd::stream_cmd_t stream_cmd(uhd::stream_cmd_t::STREAM_MODE_START_CONTINUOUS);
    stream_cmd.stream_now = true;   
    rx_stream->issue_stream_cmd(stream_cmd);
	
    while (not stop_signal_called) {
	    // Check if there is an available memory chunk, allocate one if not
	    if (freeq.empty()) {
	        std::cout << "Warning: empty free queue" << std::endl;
	        freeq.push((std::complex<short>*)malloc(sizeof(std::complex<short>)*spb));
	    }
	    
	    rx_buff = freeq.pop();
	    
        // Receive samples
        num_recvd_samps = rx_stream->recv(rx_buff, spb, md);


        // Check that right number of samps were received
        if(num_recvd_samps != spb) {
            std::cout << "Bad number of recv samples, skipping queue push" << std::endl
                      << boost::format("Recieved: %zu") % num_recvd_samps << std::endl
                      << boost::format("Requested: %zu") % spb << std::endl;
            freeq.push(rx_buff);
            continue;
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
            break;
        }        

        // Put full buffer in the full queue
        fullq.push(rx_buff);

    }

    // Stop streaming
    uhd::stream_cmd_t stream_cmd_stop(uhd::stream_cmd_t::STREAM_MODE_STOP_CONTINUOUS);
    rx_stream->issue_stream_cmd(stream_cmd_stop);

    std::cout << "Streaming stopped" << std::endl;
    
    // Interrupt and join
    consumer.interrupt();
    consumer.join();
        
    // free all memory chunks
    for (size_t i=0; i<freeq.size(); i++) {
        free(freeq.pop());
    }
    for (size_t i=0; i<fullq.size(); i++) {
        free(fullq.pop());
    }

    std::cout << "Goodbye" << std::endl;

    return 0;
}
