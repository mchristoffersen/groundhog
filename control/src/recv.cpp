#include "recv.h"

#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/thread/thread.hpp>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <iostream>

#include "tsQueue.h"

// Queues for passing data from radio download thread to triggering/stacking
// thread
tsQueue<std::complex<short> *> freeq;
tsQueue<std::complex<short> *> fullq;

size_t ampTriggerSingle(std::complex<short> *buff, size_t buff_len,
                        short trigger) {
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
    if (std::abs(buff[i].real()) > trigger) {
      return i;
    }
  }
  return buff_len;
}

// Trigger and save samples
int triggerAndStack(size_t prf, size_t spt, size_t pretrig, size_t spb,
                    size_t stack, short trigger, double fs, std::string file) {
  // Make filename
  std::ofstream fd;
  fd.open(file, std::ios::out | std::ios::binary);
  int magic0 = 0xD0D0BEEF;
  fd.write((char *)&magic0, 4);

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
  fd.write((char *)&fs, sizeof(double));
  int magic1 = 0xFEEDFACE;
  fd.write((char *)&magic1, 4);

  // Buffer and for time string
  std::string tmstr;
  boost::posix_time::ptime t;

  // Trace stacking buffer (using float for this)
  int64_t *trace = (int64_t *)calloc(spt, sizeof(int64_t));

  // Stacking tracker
  size_t stacktrack = 0;

  // Number of samples to skip after trigger
  // 95% of the way to the next trigger
  size_t skipsamp = size_t(0.95 * (fs / prf));
  size_t skipped = 0;  // skipped sample counter for loop

  // Detect first trigger, iterate through frames until one is found
  bool trig = false;
  size_t trigloc = 0;
  size_t sample_offset;
  size_t ntrace = 0;

  // buffer pointers for previous, current, next frame
  std::complex<short> *prv_buff;
  std::complex<short> *cur_buff;
  std::complex<short> *nxt_buff;

  // check if fullq has any buffers to pop
  if (fullq.size() == 0) {
    std::cout << "fullq empty - delaying 500 ms" << std::endl;
    usleep(500000);
  }

  if (fullq.size() == 0) {
    std::cout << "fullq still empty - quitting" << std::endl;
    goto CLOSE;
  }

  // Get first three frames
  prv_buff = fullq.pop();
  cur_buff = fullq.pop();
  nxt_buff = fullq.pop();

  // Print file name
  std::cout << file << ":" << std::endl;
  while (not trig) {
    trigloc = ampTriggerSingle(cur_buff, spb, trigger);

    if (trigloc == spb) {  // if no trigger detected
      // Check for death
      while (fullq.empty()) {
        // See if thread has been interrupted (and sleep for a bit if not)
        try {
          boost::this_thread::sleep(boost::posix_time::milliseconds(10));
        } catch (boost::thread_interrupted &) {
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

    if (trigloc - pretrig < 0) {
      // If some pre-trigger samples are in previous buffer
      // look-behind
      for (size_t i = 0; i < (pretrig - trigloc); i++) {
        trace[i] = trace[i] + prv_buff[spb - (pretrig - trigloc) + i].real();
      }

      // current buffer
      for (size_t i = 0; i < trigloc; i++) {
        trace[i + (pretrig - trigloc)] =
            trace[i + (pretrig - trigloc)] + cur_buff[i].real();
      }
    } else {
      // If pre-trigger samples entirely within current buffer
      for (size_t i = 0; i < pretrig; i++) {
        trace[i] = trace[i] + cur_buff[trigloc - pretrig + i].real();
      }
    }

    // Get trigger and post trigger samples (check if need to use nxt_buff)
    if (trigloc + (spt - pretrig) >= spb) {
      // If some post-trigger samples are in next buffer
      //  current buffer
      for (size_t i = 0; i < (spb - trigloc); i++) {
        trace[i + pretrig] = trace[i + pretrig] + cur_buff[i + trigloc].real();
      }

      // look ahead
      for (size_t i = 0; i < (spt - pretrig - (spb - trigloc)); i++) {
        trace[i + pretrig + (spb - trigloc)] =
            trace[i + pretrig + (spb - trigloc)] + nxt_buff[i].real();
      }
    } else {
      // Add post-trigger samples to trace
      for (size_t i = 0; i < (spt - pretrig); i++) {
        trace[i + pretrig] = trace[i + pretrig] + cur_buff[i + trigloc].real();
      }
    }

    // +1 trace
    stacktrack++;

    // Save a trace
    if (stacktrack == stack) {
      // save timestamp
      t = boost::posix_time::microsec_clock::universal_time();
      tmstr = to_iso_extended_string(t);
      fd.write(&tmstr[0], tmstr.size());

      // save trace
      fd.write((char *)trace, spt * sizeof(int64_t));
      
      // reset trace
      for (size_t i = 0; i < spt; i++) {
        trace[i] = 0;
      }
      stacktrack = 0;  // reset counter
      ntrace++;

      // force flush of i/o buffer (write to disk now!)
      std::flush(fd);

      // Print status message to screen
      std::cout << "  " << tmstr << " -- "
                << "Traces: " << ntrace << "    Free Buff: " << freeq.size()
                << "        \r" << std::flush;
    }

    // Get next trigger
    // Skip frames
    // std::cout << "Skipping frames: " << std::floor((trigloc+skipsamp)/spb)
    // << std::endl;
    for (size_t i = 0; i < std::floor((trigloc + skipsamp) / spb); i++) {
      // Check if it is time to die
      while (fullq.empty()) {
        // See if thread has been interrupted (and sleep for a bit if
        // not)
        try {
          boost::this_thread::sleep(boost::posix_time::milliseconds(10));
        } catch (boost::thread_interrupted &) {
          goto CLOSE;
        }
      }
      freeq.push(prv_buff);
      prv_buff = cur_buff;
      cur_buff = nxt_buff;
      nxt_buff = fullq.pop();
    }

    // Look for trigger in remaining samples of current frame
    sample_offset = ((trigloc + skipsamp) % spb);
    trigloc = ampTriggerSingle(cur_buff + sample_offset, spb - sample_offset,
                               trigger);
    trigloc = trigloc + sample_offset;

    if (trigloc == spb) {  // if it is not present
      trig = false;
      do {
        // Check if dead
        while (fullq.empty()) {
          // See if thread has been interrupted (and sleep for a bit if
          // not)
          try {
            boost::this_thread::sleep(boost::posix_time::milliseconds(10));
          } catch (boost::thread_interrupted &) {
            goto CLOSE;
          }
        }
        freeq.push(prv_buff);
        prv_buff = cur_buff;
        cur_buff = nxt_buff;
        nxt_buff = fullq.pop();

        trigloc = ampTriggerSingle(cur_buff, spb, trigger);

        if (trigloc == spb) {
          continue;
        }

        trig = true;
      } while (not trig);
    }
  }
CLOSE:

  // Close out
  int magic2 = 0xDEADDEAD;
  fd.write((char *)&magic2, 4);
  fd.close();
  std::cout << std::endl << "Consumer dead" << std::endl;
  return 0;
}

size_t detectPRF(std::complex<short> *buff, size_t buff_len, short trigger,
                 size_t spt, double rate) {
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
      50;  // Maximum number of trigger events to detect for auto-trigger calc
  std::vector<size_t> trig_samp(ntrig);
  size_t trig_count = 0;

  // Loop over buffer and do triggering
  size_t i = 0;
  while (i < buff_len) {
    if (std::abs(buff[i].real()) > trigger) {
      trig_samp[trig_count] = i;
      trig_count += 1;
      i += spt;
    }
    if (trig_count == ntrig) {
      break;
    }
    i += 1;
  }

  if (trig_count < 2) {
    std::cout << "Failed to trigger twice for PRF detection!" << std::endl;
    return 0;
  }

  // Calculate mean time difference between triggers
  double dt;
  for (size_t i = 0; i < trig_count - 1; i++) {
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