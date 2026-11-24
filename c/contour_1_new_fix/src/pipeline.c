#include "adaptive.h"

AdProcessResult ad_process_frame(AdFrame* frame, const AdConfig* cfg) {
  AdProcessResult result;
  AdConfig local;
  double t0;
  double t1;
  double t2;
  double t3;

  result.applied = 0;
  result.route = AD_ROUTE_NONE;
  ad_timing_fill(&result.timing, 0.0, 0.0, 0.0);

  if (cfg == 0) {
    ad_config_default(&local);
    cfg = &local;
  }

  t0 = ad_now_s();
  ad_assess_frame(frame, cfg, &result.assess);
  t1 = ad_now_s();
  result.route = ad_select_route(result.assess.v);
  t2 = ad_now_s();
  if (result.route != AD_ROUTE_NONE) {
    ad_apply_route(frame, result.route, result.assess.v, cfg);
    result.applied = 1;
  }
  t3 = ad_now_s();

  ad_timing_fill(&result.timing, t1 - t0, t2 - t1, t3 - t2);
  return result;
}
