#include "adaptive.h"

AdProcessResult ad_process_frame(AdFrame* frame, const AdConfig* cfg) {
  AdAssess assess;
  AdProcessResult result;
  AdConfig local;
  double t0;
  double t1;
  double t2;
  double t3;
  double assess_s;
  double decide_s;
  double apply_s;

  result.applied = 0;
  result.changed = 0;
  result.decision.route = AD_ROUTE_NONE;
  result.decision.state = AD_STATE_OK;
  result.decision.kind = AD_DAMAGE_NONE;
  result.decision.health = 1.0f;
  result.decision.damage = 0.0f;
  result.decision.repair_cost = 0.0f;
  result.decision.r = 0.0f;
  result.decision.gamma = 1.0f;
  result.decision.clahe_clip = 2.0f;
  result.decision.sharpen_amount = 0.0f;
  ad_timing_fill(&result.timing, 0.0, 0.0, 0.0);

  if (cfg == 0) {
    ad_config_default(&local);
    cfg = &local;
  }

  t0 = ad_now_s();
  ad_assess_frame(frame, cfg, &assess);
  t1 = ad_now_s();
  result.decision = ad_decide(&assess, cfg);
  t2 = ad_now_s();

  if (result.decision.route != AD_ROUTE_NONE) {
    ad_apply_route(frame, &result.decision, cfg);
    result.applied = 1;
    result.changed = 1;
  }
  t3 = ad_now_s();

  assess_s = t1 - t0;
  decide_s = t2 - t1;
  apply_s = t3 - t2;
  ad_timing_fill(&result.timing, assess_s, decide_s, apply_s);

  return result;
}
