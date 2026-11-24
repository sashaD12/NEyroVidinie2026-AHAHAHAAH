#include "adaptive.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fill_texture(AdFrame* frame) {
  uint32_t y;
  uint32_t x;
  for (y = 0; y < frame->height; y += 1) {
    for (x = 0; x < frame->width; x += 1) {
      uint8_t v = (uint8_t)((x * 37 + y * 91) & 255);
      frame->data[y * frame->stride + x] = v;
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
    sink += assess.v[AD_V_N] + assess.v[AD_V_B] + assess.s_L + assess.n_flat;
  }
  t_assess1 = ad_now_s();
  t_all1 = t_assess1;

  prepare_s = t_prep1 - t_prep0;
  assess_s = t_assess1 - t_assess0;
  per_s = assess_s / (double)iters;
  ad_timing_fill(&timing, assess_s, 0.0, 0.0);

  printf("contour=1\n");
  printf("source=%s\n", from_file ? path : "synthetic");
  printf("size=%ux%u\n", (unsigned)frame.width, (unsigned)frame.height);
  printf("iters=%u\n", (unsigned)iters);
  printf("mu=%.2f sigma=%.2f pb=%.4f ps=%.4f\n", assess.mu, assess.sigma, assess.pb, assess.ps);
  printf(
    "d_u=%.4f d_o=%.4f d_c=%.4f d_n=%.4f d_b=%.4f\n",
    assess.v[AD_V_U],
    assess.v[AD_V_O],
    assess.v[AD_V_C],
    assess.v[AD_V_N],
    assess.v[AD_V_B]
  );
  printf("s_L=%.4f n_flat=%.4f flat_count=%u\n", assess.s_L, assess.n_flat, (unsigned)assess.flat_count);
  printf("route=%s\n", ad_route_name(ad_select_route(assess.v)));
  printf(
    "log_kind=%s log_state=%s log_r=%.4f\n",
    ad_kind_name(assess.log_kind),
    ad_state_name(assess.log_state),
    assess.log_r
  );
  printf("prepare_s=%.6f\n", prepare_s);
  printf("prepare_ms=%.3f\n", prepare_s * 1000.0);
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
