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
  cfg->n0 = 7.1580f;
  cfg->flat_frac = 0.10f;
  cfg->tau_l = 0.48f;
  cfg->t_l = 0.90f;
  cfg->tau_n = 0.2420f;
  cfg->t_n = 1.0000f;
  cfg->tau_b = 0.1805f;
  cfg->t_b = 0.7071f;
  cfg->clahe_clip_min = 2.0f;
  cfg->clahe_clip_span = 6.0f;
  cfg->clahe_tiles_x = 8;
  cfg->clahe_tiles_y = 8;
}
