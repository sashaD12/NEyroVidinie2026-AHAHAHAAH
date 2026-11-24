#include "adaptive.h"

#include <stdio.h>
#include <string.h>

static const char* ad_route_name(AdRoute route) {
  switch (route) {
    case AD_ROUTE_NONE:
      return "NONE";
    case AD_ROUTE_GAMMA_LIGHT:
      return "GAMMA_LIGHT";
    case AD_ROUTE_GAMMA_DARK:
      return "GAMMA_DARK";
    case AD_ROUTE_STRETCH:
      return "STRETCH";
    case AD_ROUTE_CLAHE:
      return "CLAHE";
    default:
      return "UNKNOWN";
  }
}

static const char* ad_state_name(AdState state) {
  switch (state) {
    case AD_STATE_OK:
      return "OK";
    case AD_STATE_REPAIR:
      return "REPAIR";
    case AD_STATE_BAD:
      return "BAD";
    default:
      return "UNKNOWN";
  }
}

static const char* ad_kind_name(AdDamageKind kind) {
  switch (kind) {
    case AD_DAMAGE_NONE:
      return "NONE";
    case AD_DAMAGE_UNDER:
      return "UNDER";
    case AD_DAMAGE_OVER:
      return "OVER";
    case AD_DAMAGE_CONTRAST:
      return "CONTRAST";
    case AD_DAMAGE_MIXED:
      return "MIXED";
    default:
      return "UNKNOWN";
  }
}

static void ad_print_usage(const char* argv0) {
  fprintf(stderr, "Usage: %s <input.(png|jpg|bmp)> <output.(png|jpg|bmp)>\n", argv0);
}

static void ad_print_seconds_comma(const char* key, double seconds) {
  char buf[64];
  char* p;
  snprintf(buf, sizeof(buf), "%.5f", seconds);
  for (p = buf; *p != 0; p += 1) {
    if (*p == '.') {
      *p = ',';
    }
  }
  printf("%s=%s\n", key, buf);
}

int main(int argc, char** argv) {
  AdFrame frame;
  AdConfig cfg;
  AdProcessResult result;
  uint8_t* owned = 0;
  const char* in_path;
  const char* out_path;
  double t_load0;
  double t_load1;
  double t_save0;
  double t_save1;
  double load_s;
  double save_s;
  double all_s;

  if (argc != 3) {
    ad_print_usage(argv[0]);
    return 1;
  }

  in_path = argv[1];
  out_path = argv[2];

  ad_config_default(&cfg);
  t_load0 = ad_now_s();
  if (!ad_load_gray(in_path, &frame, &owned)) {
    fprintf(stderr, "Failed to load image: %s\n", in_path);
    return 2;
  }
  t_load1 = ad_now_s();

  result = ad_process_frame(&frame, &cfg);

  t_save0 = ad_now_s();
  if (!ad_save_gray(out_path, &frame)) {
    fprintf(stderr, "Failed to save image: %s\n", out_path);
    ad_free_owned(owned);
    return 3;
  }
  t_save1 = ad_now_s();

  load_s = t_load1 - t_load0;
  save_s = t_save1 - t_save0;
  all_s = load_s + result.timing.total_s + save_s;

  printf("input=%s\n", in_path);
  printf("output=%s\n", out_path);
  printf("state=%s\n", ad_state_name(result.decision.state));
  printf("kind=%s\n", ad_kind_name(result.decision.kind));
  printf("route=%s\n", ad_route_name(result.decision.route));
  printf("damage=%.4f\n", result.decision.damage);
  printf("r=%.4f\n", result.decision.r);
  printf("cost=%.4f\n", result.decision.repair_cost);
  printf("mu=%.2f\n", result.decision.assess.mu);
  printf("sigma=%.2f\n", result.decision.assess.sigma);
  printf("applied=%d\n", result.applied);

  printf("time_unit=1/100000_s\n");
  ad_print_seconds_comma("time_load_s", load_s);
  ad_print_seconds_comma("time_assess_s", result.timing.assess_s);
  ad_print_seconds_comma("time_decide_s", result.timing.decide_s);
  ad_print_seconds_comma("time_apply_s", result.timing.apply_s);
  ad_print_seconds_comma("time_save_s", save_s);
  ad_print_seconds_comma("time_core_s", result.timing.total_s);
  ad_print_seconds_comma("time_all_s", all_s);
  printf("time_load_x100000=%u\n", ad_seconds_to_x100000(load_s));
  printf("time_assess_x100000=%u\n", result.timing.assess_x100000);
  printf("time_decide_x100000=%u\n", result.timing.decide_x100000);
  printf("time_apply_x100000=%u\n", result.timing.apply_x100000);
  printf("time_save_x100000=%u\n", ad_seconds_to_x100000(save_s));
  printf("time_core_x100000=%u\n", result.timing.total_x100000);
  printf("time_all_x100000=%u\n", ad_seconds_to_x100000(all_s));

  ad_free_owned(owned);
  return 0;
}
