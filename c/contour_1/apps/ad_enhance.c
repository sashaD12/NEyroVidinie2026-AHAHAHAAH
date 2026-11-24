#include "adaptive.h"

#include <stdio.h>
#include <string.h>

static const char* ad_route_name(AdRoute route) {
  if (route == AD_ROUTE_NONE) {
    return "NONE";
  }
  if (route == AD_ROUTE_GAMMA_LIGHT) {
    return "GAMMA_LIGHT";
  }
  if (route == AD_ROUTE_GAMMA_DARK) {
    return "GAMMA_DARK";
  }
  if (route == AD_ROUTE_STRETCH) {
    return "STRETCH";
  }
  if (route == AD_ROUTE_CLAHE) {
    return "CLAHE";
  }
  if (route == AD_ROUTE_DENOISE) {
    return "DENOISE";
  }
  if (route == AD_ROUTE_SHARPEN) {
    return "SHARPEN";
  }
  return "UNKNOWN";
}

static const char* ad_state_name(AdState state) {
  if (state == AD_STATE_OK) {
    return "OK";
  }
  if (state == AD_STATE_REPAIR) {
    return "REPAIR";
  }
  if (state == AD_STATE_BAD) {
    return "BAD";
  }
  return "UNKNOWN";
}

static const char* ad_kind_name(AdDamageKind kind) {
  if (kind == AD_DAMAGE_NONE) {
    return "NONE";
  }
  if (kind == AD_DAMAGE_UNDER) {
    return "UNDER";
  }
  if (kind == AD_DAMAGE_OVER) {
    return "OVER";
  }
  if (kind == AD_DAMAGE_CONTRAST) {
    return "CONTRAST";
  }
  if (kind == AD_DAMAGE_MIXED) {
    return "MIXED";
  }
  if (kind == AD_DAMAGE_NOISE) {
    return "NOISE";
  }
  if (kind == AD_DAMAGE_BLUR) {
    return "BLUR";
  }
  return "UNKNOWN";
}

static void ad_print_usage(const char* argv0) {
  fprintf(stderr, "Usage: %s [--force] <input.(png|jpg|bmp)> <output.(png|jpg|bmp)>\n", argv0);
}

int main(int argc, char** argv) {
  AdFrame frame;
  AdConfig cfg;
  AdProcessResult result;
  uint8_t* owned = 0;
  const char* in_path = 0;
  const char* out_path = 0;
  int force = 0;
  int i;
  uint8_t c;

  for (i = 1; i < argc; i += 1) {
    if (strcmp(argv[i], "--force") == 0) {
      force = 1;
    } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
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
  cfg.force_enhance = force ? 1 : 0;
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
  printf("force=%d\n", force);
  printf("kind=%s\n", ad_kind_name(result.decision.kind));
  printf("state=%s\n", ad_state_name(result.decision.state));
  printf("route=%s\n", ad_route_name(result.decision.route));
  printf("damage=%.4f\n", result.decision.damage);
  printf("r=%.4f\n", result.decision.r);
  printf("cost=%.4f\n", result.decision.repair_cost);
  printf("gamma=%.4f\n", result.decision.gamma);
  printf("clahe_clip=%.4f\n", result.decision.clahe_clip);
  printf("sharpen_amount=%.4f\n", result.decision.sharpen_amount);
  printf("applied=%d\n", result.applied);
  printf("candidates=%u\n", (unsigned)result.decision.candidates.count);
  for (c = 0; c < result.decision.candidates.count; c += 1) {
    printf(
      "cand[%u]=%s cost=%.4f\n",
      (unsigned)c,
      ad_route_name(result.decision.candidates.items[c].route),
      result.decision.candidates.items[c].repair_cost
    );
  }
  printf("assess_s=%.6f\n", result.timing.assess_s);
  printf("decide_s=%.6f\n", result.timing.decide_s);
  printf("apply_s=%.6f\n", result.timing.apply_s);
  printf("total_s=%.6f\n", result.timing.total_s);
  printf("assess_x100000=%u\n", (unsigned)result.timing.assess_x100000);
  printf("decide_x100000=%u\n", (unsigned)result.timing.decide_x100000);
  printf("apply_x100000=%u\n", (unsigned)result.timing.apply_x100000);
  printf("total_x100000=%u\n", (unsigned)result.timing.total_x100000);

  ad_free_owned(owned);
  return 0;
}
