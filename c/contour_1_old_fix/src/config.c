#include "adaptive.h"

void ad_config_default(AdConfig* cfg) {
  if (cfg == 0) {
    return;
  }
  cfg->mu0 = 80.0f;
  cfg->mu1 = 180.0f;
  cfg->sigma0 = 40.0f;
  cfg->pmax = 0.5f;
  cfg->s_L0 = 0.3345f;
  cfg->n0 = 10.0889f;
  cfg->flat_frac = 0.10f;
  cfg->tau_l = 0.35f;
  cfg->t_l = 0.85f;
  cfg->tau_n = 0.3055f;
  cfg->t_n = 1.0000f;
  cfg->tau_b = 0.1999f;
  cfg->t_b = 0.7363f;
  cfg->clahe_clip_min = 2.0f;
  cfg->clahe_clip_span = 6.0f;
  cfg->clahe_tiles_x = 8;
  cfg->clahe_tiles_y = 8;
}
