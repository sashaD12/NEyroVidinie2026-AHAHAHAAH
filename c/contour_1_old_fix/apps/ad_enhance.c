#include "adaptive.h"

#include <stdio.h>
#include <string.h>

static void ad_print_usage(const char* argv0) {
  fprintf(stderr, "Usage: %s <input.(png|jpg|bmp)> <output.(png|jpg|bmp)>\n", argv0);
}

int main(int argc, char** argv) {
  AdFrame frame;
  AdConfig cfg;
  AdProcessResult result;
  uint8_t* owned = 0;
  const char* in_path = 0;
  const char* out_path = 0;
  int i;

  for (i = 1; i < argc; i += 1) {
    if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
      ad_print_usage(argv[0]);
      return 0;
    } else if (in_path == 0) {
      in_path = argv[i];
    } else if (out_path == 0) {
      out_path = argv[i];
    } else {
      ad_print_usage(argv[0]);
      return 1;
    }
  }

  if (in_path == 0 || out_path == 0) {
    ad_print_usage(argv[0]);
    return 1;
  }

  ad_config_default(&cfg);
  if (!ad_load_gray(in_path, &frame, &owned)) {
    fprintf(stderr, "Failed to load image: %s\n", in_path);
    return 2;
  }

  result = ad_process_frame(&frame, &cfg);

  if (!ad_save_gray(out_path, &frame)) {
    fprintf(stderr, "Failed to save image: %s\n", out_path);
    ad_free_owned(owned);
    return 3;
  }

  printf("input=%s\n", in_path);
  printf("output=%s\n", out_path);
  printf(
    "vector=%.4f %.4f %.4f %.4f %.4f\n",
    result.assess.v[AD_V_U],
    result.assess.v[AD_V_O],
    result.assess.v[AD_V_C],
    result.assess.v[AD_V_N],
    result.assess.v[AD_V_B]
  );
  printf("route=%s\n", ad_route_name(result.route));
  printf("applied=%d\n", result.applied);
  printf(
    "log_kind=%s log_state=%s log_r=%.4f\n",
    ad_kind_name(result.assess.log_kind),
    ad_state_name(result.assess.log_state),
    result.assess.log_r
  );
  printf("assess_s=%.6f\n", result.timing.assess_s);
  printf("select_s=%.6f\n", result.timing.select_s);
  printf("apply_s=%.6f\n", result.timing.apply_s);
  printf("total_s=%.6f\n", result.timing.total_s);
  printf("total_x100000=%u\n", (unsigned)result.timing.total_x100000);

  ad_free_owned(owned);
  return 0;
}
