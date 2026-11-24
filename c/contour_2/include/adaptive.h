#ifndef ADAPTIVE_H
#define ADAPTIVE_H

#include <stdint.h>

typedef enum AdDamageKind {
  AD_DAMAGE_NONE = 0,
  AD_DAMAGE_NOISE = 1,
  AD_DAMAGE_BLUR = 2
} AdDamageKind;

typedef enum AdState {
  AD_STATE_OK = 0,
  AD_STATE_REPAIR = 1,
  AD_STATE_BAD = 2
} AdState;

typedef struct AdFrame {
  uint8_t* data;
  uint16_t width;
  uint16_t height;
  uint16_t stride;
} AdFrame;

typedef struct AdSurfKeypoint {
  float x;
  float y;
  float scale;
  float response;
} AdSurfKeypoint;

typedef struct AdAssess {
  float s_L;
  float n_flat;
  float d_n;
  float d_b;
  float d_s;
  float r;
  float mean_response;
  AdDamageKind kind;
  AdState state;
  uint32_t sample_count;
  uint32_t flat_count;
  uint32_t keypoint_count;
} AdAssess;

typedef struct AdConfig {
  float s_L0;
  float n0;
  float tau_e;
  float tau_n;
  float t_n;
  float tau_b;
  float t_b;
  float hessian_thresh;
  uint16_t max_keypoints;
  uint8_t surf_octaves;
  uint8_t sample_step;
  uint8_t patch_min;
  uint8_t patch_max;
} AdConfig;

typedef struct AdTiming {
  double prepare_s;
  double assess_s;
  double total_s;
  uint32_t prepare_x100000;
  uint32_t assess_x100000;
  uint32_t total_x100000;
} AdTiming;

void ad_timing_fill(AdTiming* timing, double prepare_s, double assess_s);

void ad_config_default(AdConfig* cfg);

uint16_t ad_surf_detect(
  const AdFrame* frame,
  const AdConfig* cfg,
  AdSurfKeypoint* out_kps,
  uint16_t max_out,
  float* mean_response
);

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out);

double ad_now_s(void);
uint32_t ad_seconds_to_x100000(double seconds);

int ad_load_gray(const char* path, AdFrame* frame, uint8_t** owned);
void ad_free_owned(uint8_t* owned);

#endif
