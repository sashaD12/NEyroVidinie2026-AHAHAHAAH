#include "adaptive.h"
#include <stdio.h>
int main(int argc, char** argv) {
  AdConfig cfg; AdAssess a; AdFrame f; uint8_t* owned=0; AdDecision d;
  if (argc < 2) return 1;
  ad_config_default(&cfg);
  if (!ad_load_gray(argv[1], &f, &owned)) return 2;
  ad_assess_frame(&f, &cfg, &a);
  d = ad_decide(&a, &cfg);
  printf("file=%s kind=%d state=%d mu=%.1f sigma=%.1f d_u=%.3f d_o=%.3f d_c=%.3f d_l=%.3f s_L=%.1f n_flat=%.2f d_n=%.3f d_b=%.3f d_s=%.3f r=%.3f route=%d\n",
    argv[1], (int)a.kind, (int)a.state, a.mu, a.sigma, a.d_u, a.d_o, a.d_c, a.d_l, a.s_L, a.n_flat, a.d_n, a.d_b, a.d_s, a.r, (int)d.route);
  ad_free_owned(owned);
  return 0;
}
