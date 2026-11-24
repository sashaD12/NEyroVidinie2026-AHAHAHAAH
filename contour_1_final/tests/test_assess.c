#include "adaptive.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TW 640
#define TH 360

static int failures = 0;

static void check(int ok, const char* name) {
  printf("%s %s\n", ok ? "PASS" : "FAIL", name);
  if (!ok) {
    failures += 1;
  }
}

static uint32_t rng_state = 12345u;

static float rng_uniform(void) {
  rng_state = rng_state * 1664525u + 1013904223u;
  return ((float)(rng_state >> 8) + 0.5f) / 16777216.0f;
}

static float rng_normal(void) {
  float u1 = rng_uniform();
  float u2 = rng_uniform();
  return sqrtf(-2.0f * logf(u1)) * cosf(6.2831853f * u2);
}

static uint8_t clamp_u8(float v) {
  if (v < 0.0f) {
    return 0;
  }
  if (v > 255.0f) {
    return 255;
  }
  return (uint8_t)(v + 0.5f);
}

static void make_scene(uint8_t* img) {
  int i;
  int x;
  int y;
  for (y = 0; y < TH; y += 1) {
    for (x = 0; x < TW; x += 1) {
      img[y * TW + x] = (uint8_t)(110 + (x / 40 + y / 30) % 3 * 10);
    }
  }
  for (i = 0; i < 60; i += 1) {
    int w = 10 + (int)(rng_uniform() * 50.0f);
    int h = 10 + (int)(rng_uniform() * 50.0f);
    int x0 = (int)(rng_uniform() * (float)(TW - w));
    int y0 = (int)(rng_uniform() * (float)(TH - h));
    uint8_t c = (uint8_t)(40 + (int)(rng_uniform() * 170.0f));
    for (y = y0; y < y0 + h; y += 1) {
      for (x = x0; x < x0 + w; x += 1) {
        img[y * TW + x] = c;
      }
    }
  }
}

static void box_blur_x(const uint8_t* src, uint8_t* dst, int len) {
  int x;
  int y;
  int k;
  int half = len / 2;
  for (y = 0; y < TH; y += 1) {
    for (x = 0; x < TW; x += 1) {
      int sum = 0;
      int cnt = 0;
      for (k = -half; k <= half; k += 1) {
        int xx = x + k;
        if (xx < 0 || xx >= TW) {
          continue;
        }
        sum += src[y * TW + xx];
        cnt += 1;
      }
      dst[y * TW + x] = (uint8_t)((sum + cnt / 2) / cnt);
    }
  }
}

static void add_noise(const uint8_t* src, uint8_t* dst, float sigma) {
  int i;
  for (i = 0; i < TW * TH; i += 1) {
    dst[i] = clamp_u8((float)src[i] + sigma * rng_normal());
  }
}

static AdFrame frame_of(uint8_t* data, int w, int h) {
  AdFrame f;
  f.data = data;
  f.width = (uint16_t)w;
  f.height = (uint16_t)h;
  f.stride = (uint16_t)w;
  return f;
}

int main(void) {
  AdConfig cfg;
  AdAssess a;
  AdFrame f;
  uint8_t* scene = (uint8_t*)malloc(TW * TH);
  uint8_t* work = (uint8_t*)malloc(TW * TH);
  uint8_t* copy = (uint8_t*)malloc(TW * TH);
  uint8_t tiny[4] = {10, 200, 30, 90};
  float sigmas[4] = {0.0f, 5.0f, 10.0f, 20.0f};
  int lens[4] = {1, 5, 9, 15};
  float prev;
  float prev_sl;
  float first_db;
  int ok;
  int i;
  int r;
  AdProcessResult pr;

  if (scene == 0 || work == 0 || copy == 0) {
    printf("FAIL alloc\n");
    return 1;
  }
  ad_config_default(&cfg);

  memset(work, 128, TW * TH);
  f = frame_of(work, TW, TH);
  ad_assess_frame(&f, &cfg, &a);
  check(a.v[AD_V_N] == 0.0f, "flat frame gives d_n = 0");
  check(a.flat_count == (uint32_t)(cfg.flat_frac * (float)(AD_ASSESS_W * AD_ASSESS_H) + 0.5f), "relative mask takes fixed share of points");

  f = frame_of(tiny, 2, 2);
  ad_assess_frame(&f, &cfg, &a);
  check(a.flat_count == 0 && a.v[AD_V_N] == 0.0f, "no valid points gives flat_count = 0 and d_n = 0");
  for (i = 0; i < AD_VEC_DIM; i += 1) {
    check(a.v[i] >= 0.0f && a.v[i] <= 1.0f, "tiny frame vector in [0, 1]");
  }

  make_scene(scene);
  ok = 1;
  prev = -1.0f;
  for (i = 0; i < 4; i += 1) {
    add_noise(scene, work, sigmas[i]);
    f = frame_of(work, TW, TH);
    ad_assess_frame(&f, &cfg, &a);
    printf("  sigma=%.0f n_flat=%.4f d_n=%.4f flat_count=%u\n", sigmas[i], a.n_flat, a.v[AD_V_N], (unsigned)a.flat_count);
    if (a.n_flat <= prev) {
      ok = 0;
    }
    prev = a.n_flat;
  }
  check(ok, "n_flat grows with noise sigma");

  ok = 1;
  prev = -1.0f;
  prev_sl = 1.0e30f;
  first_db = -1.0f;
  for (i = 0; i < 4; i += 1) {
    box_blur_x(scene, work, lens[i]);
    f = frame_of(work, TW, TH);
    ad_assess_frame(&f, &cfg, &a);
    printf("  L=%d s_L=%.2f d_b=%.4f\n", lens[i], a.s_L, a.v[AD_V_B]);
    if (a.v[AD_V_B] < prev || a.s_L >= prev_sl) {
      ok = 0;
    }
    if (first_db < 0.0f) {
      first_db = a.v[AD_V_B];
    }
    prev = a.v[AD_V_B];
    prev_sl = a.s_L;
  }
  check(ok, "d_b does not decrease with blur length L");
  check(prev > first_db, "d_b at L=15 above d_b at L=1");

  ok = 1;
  prev = -1.0f;
  for (i = 0; i < 4; i += 1) {
    box_blur_x(scene, copy, 9);
    add_noise(copy, work, sigmas[i]);
    f = frame_of(work, TW, TH);
    ad_assess_frame(&f, &cfg, &a);
    printf("  L=9 sigma=%.0f noise_sigma=%.2f s_L=%.3f s_L_raw=%.1f d_b=%.4f\n", sigmas[i], a.noise_sigma, a.s_L, a.s_L_raw, a.v[AD_V_B]);
    if (prev >= 0.0f && fabsf(a.v[AD_V_B] - prev) > 0.25f) {
      ok = 0;
    }
    prev = a.v[AD_V_B];
  }
  check(ok, "d_b at fixed L stays stable when noise is added");

  add_noise(scene, work, 8.0f);
  f = frame_of(work, TW, TH);
  ad_assess_frame(&f, &cfg, &a);
  for (r = 0; r < (int)AD_ROUTE_COUNT; r += 1) {
    memcpy(copy, work, TW * TH);
    f = frame_of(copy, TW, TH);
    ad_apply_route(&f, (AdRoute)r, a.v, &cfg);
    if (r == (int)AD_ROUTE_NONE) {
      check(memcmp(copy, work, TW * TH) == 0, "route NONE keeps frame");
    }
    memcpy(tiny, "\x0a\xc8\x1e\x5a", 4);
    f = frame_of(tiny, 2, 2);
    ad_apply_route(&f, (AdRoute)r, a.v, &cfg);
  }
  check(1, "all routes run on 640x360 and 2x2 frames");

  check((int)ad_select_route(a.v) < (int)AD_ROUTE_COUNT, "selector returns a valid route");
  memcpy(copy, work, TW * TH);
  f = frame_of(copy, TW, TH);
  pr = ad_process_frame(&f, &cfg);
  check((int)pr.route < (int)AD_ROUTE_COUNT && pr.timing.total_s >= 0.0, "process_frame runs assess, select, apply");
  printf("  route=%s total_s=%.6f\n", ad_route_name(pr.route), pr.timing.total_s);

  free(scene);
  free(work);
  free(copy);
  printf("%s (%d failures)\n", failures == 0 ? "ALL PASS" : "FAILED", failures);
  return failures == 0 ? 0 : 1;
}
