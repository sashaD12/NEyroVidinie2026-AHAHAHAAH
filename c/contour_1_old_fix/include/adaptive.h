#ifndef ADAPTIVE_H
#define ADAPTIVE_H

#include <stdint.h>

#ifndef AD_ASSESS_W
#define AD_ASSESS_W 160
#endif

#ifndef AD_ASSESS_H
#define AD_ASSESS_H 120
#endif

#define AD_HIST_BINS 256
#define AD_GRAD_BINS 511
#define AD_VEC_DIM 5

typedef enum AdVecIndex {
  AD_V_U = 0,
  AD_V_O = 1,
  AD_V_C = 2,
  AD_V_N = 3,
  AD_V_B = 4
} AdVecIndex;

typedef enum AdDamageKind {
  AD_DAMAGE_NONE = 0,
  AD_DAMAGE_UNDER = 1,
  AD_DAMAGE_OVER = 2,
  AD_DAMAGE_CONTRAST = 3,
  AD_DAMAGE_MIXED = 4,
  AD_DAMAGE_NOISE = 5,
  AD_DAMAGE_BLUR = 6
} AdDamageKind;

typedef enum AdState {
  AD_STATE_OK = 0,
  AD_STATE_REPAIR = 1,
  AD_STATE_BAD = 2
} AdState;

typedef enum AdRoute {
  AD_ROUTE_NONE = 0,
  AD_ROUTE_GAMMA = 1,
  AD_ROUTE_DEOVER = 2,
  AD_ROUTE_STRETCH = 3,
  AD_ROUTE_CLAHE = 4,
  AD_ROUTE_DENOISE = 5,
  AD_ROUTE_SHARPEN = 6,
  AD_ROUTE_COUNT = 7
} AdRoute;

typedef struct AdFrame {
  uint8_t* data;
  uint16_t width;
  uint16_t height;
  uint16_t stride;
} AdFrame;

typedef struct AdAssess {
  float v[AD_VEC_DIM];
  float mu;
  float sigma;
  float pb;
  float ps;
  float s_L;
  float s_L_raw;
  float noise_sigma;
  float n_flat;
  float aniso;
  float e_max;
  float d_motion;
  uint32_t hist[AD_HIST_BINS];
  uint32_t sample_count;
  uint32_t flat_count;
  AdDamageKind log_kind;
  AdState log_state;
  float log_r;
} AdAssess;

typedef struct AdConfig {
  float mu0;
  float mu1;
  float sigma0;
  float pmax;
  float s_L0;
  float n0;
  float flat_frac;
  float tau_l;
  float t_l;
  float tau_n;
  float t_n;
  float tau_b;
  float t_b;
  float clahe_clip_min;
  float clahe_clip_span;
  uint8_t clahe_tiles_x;
  uint8_t clahe_tiles_y;
} AdConfig;

typedef struct AdTreeNode {
  double threshold;
  int16_t feature;
  int16_t left;
  int16_t right;
  uint8_t route;
} AdTreeNode;

extern const AdTreeNode ad_tree_nodes[];
extern const uint32_t ad_tree_size;

typedef struct AdTiming {
  double assess_s;
  double select_s;
  double apply_s;
  double total_s;
  uint32_t assess_x100000;
  uint32_t select_x100000;
  uint32_t apply_x100000;
  uint32_t total_x100000;
} AdTiming;

typedef struct AdProcessResult {
  AdAssess assess;
  AdRoute route;
  AdTiming timing;
  int applied;
} AdProcessResult;

void ad_config_default(AdConfig* cfg);

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out);

AdRoute ad_select_route(const float* v);

void ad_apply_route(AdFrame* frame, AdRoute route, const float* v, const AdConfig* cfg);

AdProcessResult ad_process_frame(AdFrame* frame, const AdConfig* cfg);

const char* ad_route_name(AdRoute route);
const char* ad_kind_name(AdDamageKind kind);
const char* ad_state_name(AdState state);

void ad_timing_fill(AdTiming* timing, double assess_s, double select_s, double apply_s);

double ad_now_s(void);
uint32_t ad_seconds_to_x100000(double seconds);

int ad_load_gray(const char* path, AdFrame* frame, uint8_t** owned);
int ad_save_gray(const char* path, const AdFrame* frame);
void ad_free_owned(uint8_t* owned);

#endif
