#include "adaptive.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char* ad_kind_name(AdDamageKind kind) {
  if (kind == AD_DAMAGE_NOISE) {
    return "noise";
  }
  if (kind == AD_DAMAGE_BLUR) {
    return "blur";
  }
  return "none";
}

static const char* ad_state_name(AdState state) {
  if (state == AD_STATE_REPAIR) {
    return "repair";
  }
  if (state == AD_STATE_BAD) {
    return "bad";
  }
  return "ok";
}

static void fill_texture(AdFrame* frame) {
  uint32_t y;
  uint32_t x;
  uint32_t bi;
  for (y = 0; y < frame->height; y += 1) {
    for (x = 0; x < frame->width; x += 1) {
      uint8_t v = (uint8_t)(40 + ((x + y) % 50));
      frame->data[y * frame->stride + x] = v;
    }
  }
  for (bi = 0; bi < 24; bi += 1) {
    int32_t cx = (int32_t)((bi * 97 + 40) % (frame->width > 80 ? frame->width - 40 : 1));
    int32_t cy = (int32_t)((bi * 53 + 30) % (frame->height > 80 ? frame->height - 40 : 1));
    int32_t rad = 8 + (int32_t)(bi % 7);
    int32_t yy;
    int32_t xx;
    if (cx < rad) {
      cx = rad;
    }
    if (cy < rad) {
      cy = rad;
    }
    for (yy = -rad; yy <= rad; yy += 1) {
      for (xx = -rad; xx <= rad; xx += 1) {
        if (xx * xx + yy * yy <= rad * rad) {
          int32_t px = cx + xx;
          int32_t py = cy + yy;
          if (px >= 0 && py >= 0 && px < (int32_t)frame->width && py < (int32_t)frame->height) {
            frame->data[(uint32_t)py * frame->stride + (uint32_t)px] = 220;
          }
        }
      }
    }
  }
}

static AdFrame make_frame(uint16_t w, uint16_t h, uint8_t** owned) {
  AdFrame frame;
  frame.width = w;
  frame.height = h;
  frame.stride = w;
  frame.data = (uint8_t*)calloc((size_t)w * (size_t)h, 1);
  *owned = frame.data;
  return frame;
}

static void print_usage(const char* argv0) {
  fprintf(stderr, "usage: %s [image] [--iters N] [--w W] [--h H]\n", argv0);
}

int main(int argc, char** argv) {
  AdConfig cfg;
  AdAssess assess;
  AdTiming timing;
  AdFrame frame;
  uint8_t* owned = 0;
  int from_file = 0;
  uint32_t iters = 200;
  uint16_t syn_w = 1920;
  uint16_t syn_h = 1080;
  const char* path = 0;
  uint32_t i;
  double t_all0;
  double t_prep0;
  double t_prep1;
  double t_assess0;
  double t_assess1;
  double t_all1;
  double prepare_s;
  double assess_s;
  double per_s;
  volatile float sink = 0.0f;

  for (i = 1; i < (uint32_t)argc; i += 1) {
    if (strcmp(argv[i], "--iters") == 0 && i + 1 < (uint32_t)argc) {
      i += 1;
      iters = (uint32_t)atoi(argv[i]);
      if (iters == 0) {
        iters = 1;
      }
    } else if (strcmp(argv[i], "--w") == 0 && i + 1 < (uint32_t)argc) {
      i += 1;
      syn_w = (uint16_t)atoi(argv[i]);
    } else if (strcmp(argv[i], "--h") == 0 && i + 1 < (uint32_t)argc) {
      i += 1;
      syn_h = (uint16_t)atoi(argv[i]);
    } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
      print_usage(argv[0]);
      return 0;
    } else if (argv[i][0] == '-') {
      fprintf(stderr, "unknown flag: %s\n", argv[i]);
      print_usage(argv[0]);
      return 1;
    } else {
      path = argv[i];
    }
  }

  t_all0 = ad_now_s();
  t_prep0 = t_all0;

  ad_config_default(&cfg);

  if (path != 0) {
    if (!ad_load_gray(path, &frame, &owned)) {
      fprintf(stderr, "failed to load: %s\n", path);
      return 1;
    }
    from_file = 1;
  } else {
    if (syn_w == 0 || syn_h == 0) {
      fprintf(stderr, "invalid synthetic size\n");
      return 1;
    }
    frame = make_frame(syn_w, syn_h, &owned);
    if (owned == 0) {
      fprintf(stderr, "alloc failed\n");
      return 1;
    }
    fill_texture(&frame);
  }

  ad_assess_frame(&frame, &cfg, &assess);
  t_prep1 = ad_now_s();

  t_assess0 = t_prep1;
  for (i = 0; i < iters; i += 1) {
    ad_assess_frame(&frame, &cfg, &assess);
    sink += assess.d_s + assess.s_L + assess.n_flat + (float)assess.keypoint_count;
  }
  t_assess1 = ad_now_s();
  t_all1 = t_assess1;

  prepare_s = t_prep1 - t_prep0;
  assess_s = t_assess1 - t_assess0;
  per_s = assess_s / (double)iters;
  ad_timing_fill(&timing, prepare_s, assess_s);

  printf("contour=2\n");
  printf("detector=surf_keypoints\n");
  printf("source=%s\n", from_file ? path : "synthetic");
  printf("size=%ux%u\n", (unsigned)frame.width, (unsigned)frame.height);
  printf("iters=%u\n", (unsigned)iters);
  printf("keypoints=%u mean_response=%.4f\n",
         (unsigned)assess.keypoint_count, assess.mean_response);
  printf("kind=%s state=%s\n", ad_kind_name(assess.kind), ad_state_name(assess.state));
  printf("s_L=%.4f n_flat=%.4f d_n=%.4f d_b=%.4f d_s=%.4f r=%.4f\n",
         assess.s_L, assess.n_flat, assess.d_n, assess.d_b, assess.d_s, assess.r);
  printf("prepare_s=%.6f\n", timing.prepare_s);
  printf("prepare_ms=%.3f\n", timing.prepare_s * 1000.0);
  printf("assess_loop_s=%.6f\n", timing.assess_s);
  printf("assess_per_frame_s=%.6f\n", per_s);
  printf("assess_per_frame_ms=%.3f\n", per_s * 1000.0);
  printf("assess_fps=%.1f\n", (per_s > 0.0) ? (1.0 / per_s) : 0.0);
  printf("total_s=%.6f\n", timing.total_s);
  printf("total_ms=%.3f\n", timing.total_s * 1000.0);
  printf("total_x100000=%u\n", (unsigned)timing.total_x100000);
  printf("wall_s=%.6f\n", t_all1 - t_all0);
  printf("sink=%.6f\n", (double)sink);

  if (from_file) {
    ad_free_owned(owned);
  } else {
    free(owned);
  }
  return 0;
}
