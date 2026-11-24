#include "adaptive.h"

void ad_config_default(AdConfig* cfg) {
  if (cfg == 0) {
    return;
  }
  cfg->s_L0 = 100.0f;
  cfg->n0 = 8.0f;
  cfg->tau_e = 24.0f;
  cfg->tau_n = 0.35f;
  cfg->t_n = 0.85f;
  cfg->tau_b = 0.35f;
  cfg->t_b = 0.85f;
  cfg->hessian_thresh = 0.5f;
  cfg->max_keypoints = 96;
  cfg->surf_octaves = 2;
  cfg->sample_step = 2;
  cfg->patch_min = 7;
  cfg->patch_max = 15;
}
