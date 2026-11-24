#include "adaptive.h"

void ad_config_default(AdConfig* cfg) {
  if (cfg == 0) {
    return;
  }
  cfg->mu0 = 80.0f;
  cfg->mu1 = 180.0f;
  cfg->sigma0 = 40.0f;
  cfg->pmax = 0.5f;
  cfg->tau_l = 0.48f;
  cfg->t_l = 0.90f;
  cfg->s_L0 = 4500.0f;
  cfg->n0 = 3.8f;
  cfg->tau_e = 12.0f;
  cfg->tau_n = 0.34f;
  cfg->t_n = 0.88f;
  cfg->tau_b = 0.25f;
  cfg->t_b = 0.82f;
  cfg->cost_base_point = 0.08f;
  cfg->cost_per_r_point = 1.0f;
  cfg->cost_base_spatial = 0.25f;
  cfg->cost_per_r_spatial = 1.2f;
  cfg->cost_base_clahe = 0.80f;
  cfg->cost_per_r_clahe = 2.0f;
  cfg->clahe_clip_min = 2.0f;
  cfg->clahe_clip_span = 6.0f;
  cfg->clahe_tiles_x = 8;
  cfg->clahe_tiles_y = 8;
  cfg->force_enhance = 0;
}
