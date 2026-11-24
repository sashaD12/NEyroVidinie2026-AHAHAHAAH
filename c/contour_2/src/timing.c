#include "adaptive.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

double ad_now_s(void) {
#ifdef _WIN32
  static LARGE_INTEGER freq;
  static int ready = 0;
  LARGE_INTEGER counter;
  if (!ready) {
    QueryPerformanceFrequency(&freq);
    ready = 1;
  }
  QueryPerformanceCounter(&counter);
  return (double)counter.QuadPart / (double)freq.QuadPart;
#else
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec * 1.0e-9;
#endif
}

uint32_t ad_seconds_to_x100000(double seconds) {
  double scaled;
  if (seconds <= 0.0) {
    return 0;
  }
  scaled = seconds * 100000.0 + 0.5;
  if (scaled > 4294967295.0) {
    return 4294967295u;
  }
  return (uint32_t)scaled;
}

void ad_timing_fill(AdTiming* timing, double prepare_s, double assess_s) {
  if (timing == 0) {
    return;
  }
  timing->prepare_s = prepare_s;
  timing->assess_s = assess_s;
  timing->total_s = prepare_s + assess_s;
  timing->prepare_x100000 = ad_seconds_to_x100000(prepare_s);
  timing->assess_x100000 = ad_seconds_to_x100000(assess_s);
  timing->total_x100000 = ad_seconds_to_x100000(timing->total_s);
}
