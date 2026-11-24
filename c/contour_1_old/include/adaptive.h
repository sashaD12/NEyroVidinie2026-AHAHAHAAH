#ifndef ADAPTIVE_H
#define ADAPTIVE_H

#include <stdint.h>

#ifndef AD_ASSESS_W
#define AD_ASSESS_W 160
#endif

#ifndef AD_ASSESS_H
#define AD_ASSESS_H 120
#endif

#ifndef AD_MAX_CANDIDATES
#define AD_MAX_CANDIDATES 8
#endif

#define AD_HIST_BINS 256

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
  AD_ROUTE_GAMMA_LIGHT = 1,
  AD_ROUTE_GAMMA_DARK = 2,
  AD_ROUTE_STRETCH = 3,
  AD_ROUTE_CLAHE = 4,
  AD_ROUTE_DENOISE = 5,
  AD_ROUTE_SHARPEN = 6
} AdRoute;

typedef struct AdFrame {
  uint8_t* data;
  uint16_t width;
  uint16_t height;
  uint16_t stride;
} AdFrame;

typedef struct AdAssess {
  float mu;
  float sigma;
  float pb;
  float ps;
  float d_u;
  float d_o;
  float d_c;
  float d_l;
  float s_L;
  float n_flat;
  float d_n;
  float d_b;
  float d_s;
  float r;
  AdDamageKind kind;
  AdState state;
  uint32_t hist[AD_HIST_BINS];
  uint32_t sample_count;
  uint32_t flat_count;
} AdAssess;

typedef struct AdRouteCandidate {
  AdRoute route;
  float repair_cost;
  float gamma;
  float clahe_clip;
  float sharpen_amount;
} AdRouteCandidate;

typedef struct AdCandidateList {
  AdRouteCandidate items[AD_MAX_CANDIDATES];
  uint8_t count;
} AdCandidateList;

typedef struct AdDecision {
  AdRoute route;
  AdState state;
  AdDamageKind kind;
  float health;
  float damage;
  float repair_cost;
  float r;
  float gamma;
  float clahe_clip;
  float sharpen_amount;
  AdAssess assess;
  AdCandidateList candidates;
} AdDecision;

typedef struct AdConfig {
  float mu0;
  float mu1;
  float sigma0;
  float pmax;
  float tau_l;
  float t_l;
  float s_L0;
  float n0;
  float tau_e;
  float tau_n;
  float t_n;
  float tau_b;
  float t_b;
  float cost_base_point;
  float cost_per_r_point;
  float cost_base_spatial;
  float cost_per_r_spatial;
  float cost_base_clahe;
  float cost_per_r_clahe;
  float clahe_clip_min;
  float clahe_clip_span;
  uint8_t clahe_tiles_x;
  uint8_t clahe_tiles_y;
} AdConfig;

typedef struct AdTiming {
  double assess_s;
  double decide_s;
  double apply_s;
  double total_s;
  uint32_t assess_x100000;
  uint32_t decide_x100000;
  uint32_t apply_x100000;
  uint32_t total_x100000;
} AdTiming;

typedef struct AdProcessResult {
  AdDecision decision;
  AdTiming timing;
  int applied;
  int changed;
} AdProcessResult;

void ad_config_default(AdConfig* cfg);

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out);

void ad_decide_candidates(const AdAssess* assess, const AdConfig* cfg, AdCandidateList* out);

AdDecision ad_pick_cheapest(const AdAssess* assess, const AdConfig* cfg, const AdCandidateList* candidates);

AdDecision ad_decide(const AdAssess* assess, const AdConfig* cfg);

void ad_apply_route(AdFrame* frame, const AdDecision* decision, const AdConfig* cfg);

AdProcessResult ad_process_frame(AdFrame* frame, const AdConfig* cfg);

void ad_timing_fill(AdTiming* timing, double assess_s, double decide_s, double apply_s);

double ad_now_s(void);
uint32_t ad_seconds_to_x100000(double seconds);

int ad_load_gray(const char* path, AdFrame* frame, uint8_t** owned);
int ad_save_gray(const char* path, const AdFrame* frame);
void ad_free_owned(uint8_t* owned);

#endif
