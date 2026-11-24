#include "adaptive.h"

#include <math.h>
#include <stdlib.h>

static float ad_clamp01(float x) {
  if (x < 0.0f) {
    return 0.0f;
  }
  if (x > 1.0f) {
    return 1.0f;
  }
  return x;
}

static float ad_severity_r(float d, float tau, float t) {
  if (d <= tau) {
    return 0.0f;
  }
  if (d >= t) {
    return 1.0f;
  }
  if (t <= tau) {
    return 1.0f;
  }
  return (d - tau) / (t - tau);
}

static int32_t ad_iabs(int32_t v) {
  if (v < 0) {
    return -v;
  }
  return v;
}

static uint8_t ad_sample(const AdFrame* frame, int32_t x, int32_t y) {
  if (x < 0) {
    x = 0;
  }
  if (y < 0) {
    y = 0;
  }
  if (x >= (int32_t)frame->width) {
    x = (int32_t)frame->width - 1;
  }
  if (y >= (int32_t)frame->height) {
    y = (int32_t)frame->height - 1;
  }
  return frame->data[(uint32_t)y * (uint32_t)frame->stride + (uint32_t)x];
}

static int32_t ad_patch_radius(const AdConfig* cfg, float scale) {
  float r = scale * 3.0f;
  int32_t ri;
  if (r < (float)cfg->patch_min) {
    r = (float)cfg->patch_min;
  }
  if (r > (float)cfg->patch_max) {
    r = (float)cfg->patch_max;
  }
  ri = (int32_t)(r + 0.5f);
  if (ri < 3) {
    ri = 3;
  }
  return ri;
}

static void ad_patch_metrics(
  const AdFrame* frame,
  const AdConfig* cfg,
  int32_t cx,
  int32_t cy,
  int32_t radius,
  double* lap_sum,
  double* lap_sum_sq,
  uint32_t* lap_n,
  double* flat_sum,
  uint32_t* flat_n
) {
  int32_t y;
  int32_t x;

  for (y = cy - radius + 1; y <= cy + radius - 1; y += 1) {
    for (x = cx - radius + 1; x <= cx + radius - 1; x += 1) {
      int32_t c;
      int32_t L;
      float Lf;
      uint8_t p00;
      uint8_t p10;
      uint8_t pm10;
      uint8_t p01;
      uint8_t p0m1;
      int32_t sum3;
      uint8_t yy;
      uint8_t xx;
      float mean3;
      float residual;
      float grad;

      c = (int32_t)ad_sample(frame, x, y);
      L = (int32_t)ad_sample(frame, x + 1, y)
        + (int32_t)ad_sample(frame, x - 1, y)
        + (int32_t)ad_sample(frame, x, y + 1)
        + (int32_t)ad_sample(frame, x, y - 1)
        - 4 * c;
      Lf = (float)L;
      *lap_sum += (double)Lf;
      *lap_sum_sq += (double)Lf * (double)Lf;
      *lap_n += 1;

      p00 = ad_sample(frame, x, y);
      p10 = ad_sample(frame, x + 1, y);
      pm10 = ad_sample(frame, x - 1, y);
      p01 = ad_sample(frame, x, y + 1);
      p0m1 = ad_sample(frame, x, y - 1);

      sum3 = 0;
      for (yy = 0; yy < 3; yy += 1) {
        for (xx = 0; xx < 3; xx += 1) {
          sum3 += (int32_t)ad_sample(frame, x + (int32_t)xx - 1, y + (int32_t)yy - 1);
        }
      }
      mean3 = (float)sum3 / 9.0f;
      residual = fabsf((float)p00 - mean3);
      grad = (float)ad_iabs((int32_t)p10 - (int32_t)pm10)
        + (float)ad_iabs((int32_t)p01 - (int32_t)p0m1);
      if (grad < cfg->tau_e) {
        *flat_sum += (double)residual;
        *flat_n += 1;
      }
    }
  }
}

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out) {
  AdSurfKeypoint* kps = 0;
  uint16_t max_k;
  uint16_t kp_count;
  float mean_resp;
  uint16_t i;
  double lap_sum;
  double lap_sum_sq;
  double flat_sum;
  uint32_t lap_n;
  uint32_t flat_n;
  float s_L;
  float n_flat;
  float d_n;
  float d_b;
  float d_s;
  float r_n;
  float r_b;
  float r;
  AdDamageKind kind;

  if (out == 0) {
    return;
  }

  out->s_L = 0.0f;
  out->n_flat = 0.0f;
  out->d_n = 0.0f;
  out->d_b = 0.0f;
  out->d_s = 0.0f;
  out->r = 0.0f;
  out->mean_response = 0.0f;
  out->kind = AD_DAMAGE_NONE;
  out->state = AD_STATE_OK;
  out->sample_count = 0;
  out->flat_count = 0;
  out->keypoint_count = 0;

  if (frame == 0 || cfg == 0 || frame->data == 0 || frame->width == 0 || frame->height == 0) {
    return;
  }

  max_k = cfg->max_keypoints;
  if (max_k == 0) {
    max_k = 64;
  }
  kps = (AdSurfKeypoint*)calloc((size_t)max_k, sizeof(AdSurfKeypoint));
  if (kps == 0) {
    return;
  }

  kp_count = ad_surf_detect(frame, cfg, kps, max_k, &mean_resp);
  out->keypoint_count = kp_count;
  out->mean_response = mean_resp;
  out->sample_count = kp_count;

  if (kp_count == 0) {
    free(kps);
    d_b = 1.0f;
    d_n = 0.0f;
    d_s = 1.0f;
    r = ad_severity_r(d_b, cfg->tau_b, cfg->t_b);
    out->d_n = d_n;
    out->d_b = d_b;
    out->d_s = d_s;
    out->r = r;
    out->kind = AD_DAMAGE_BLUR;
    if (r <= 0.0f) {
      out->state = AD_STATE_OK;
      out->kind = AD_DAMAGE_NONE;
    } else if (r >= 1.0f) {
      out->state = AD_STATE_BAD;
    } else {
      out->state = AD_STATE_REPAIR;
    }
    return;
  }

  lap_sum = 0.0;
  lap_sum_sq = 0.0;
  flat_sum = 0.0;
  lap_n = 0;
  flat_n = 0;

  for (i = 0; i < kp_count; i += 1) {
    int32_t cx = (int32_t)(kps[i].x + 0.5f);
    int32_t cy = (int32_t)(kps[i].y + 0.5f);
    int32_t radius = ad_patch_radius(cfg, kps[i].scale);
    ad_patch_metrics(
      frame,
      cfg,
      cx,
      cy,
      radius,
      &lap_sum,
      &lap_sum_sq,
      &lap_n,
      &flat_sum,
      &flat_n
    );
  }

  free(kps);

  s_L = 0.0f;
  if (lap_n > 0) {
    double mean_L = lap_sum / (double)lap_n;
    double var_L = (lap_sum_sq / (double)lap_n) - (mean_L * mean_L);
    if (var_L < 0.0) {
      var_L = 0.0;
    }
    s_L = (float)var_L;
  }

  n_flat = 0.0f;
  if (flat_n > 0) {
    n_flat = (float)(flat_sum / (double)flat_n);
  }

  if (cfg->s_L0 > 0.0f) {
    d_b = ad_clamp01(1.0f - (s_L / cfg->s_L0));
  } else {
    d_b = 0.0f;
  }

  if (cfg->n0 > 0.0f) {
    d_n = ad_clamp01(n_flat / cfg->n0);
  } else {
    d_n = 0.0f;
  }

  d_s = fmaxf(d_n, d_b);
  r_n = ad_severity_r(d_n, cfg->tau_n, cfg->t_n);
  r_b = ad_severity_r(d_b, cfg->tau_b, cfg->t_b);

  kind = AD_DAMAGE_NONE;
  r = 0.0f;
  if (d_n >= cfg->tau_n && d_b >= cfg->tau_b) {
    if (d_b > d_n) {
      kind = AD_DAMAGE_BLUR;
      r = r_b;
    } else {
      kind = AD_DAMAGE_NOISE;
      r = r_n;
    }
  } else if (d_n >= cfg->tau_n) {
    kind = AD_DAMAGE_NOISE;
    r = r_n;
  } else if (d_b >= cfg->tau_b) {
    kind = AD_DAMAGE_BLUR;
    r = r_b;
  }

  out->s_L = s_L;
  out->n_flat = n_flat;
  out->d_n = d_n;
  out->d_b = d_b;
  out->d_s = d_s;
  out->r = r;
  out->kind = kind;
  out->flat_count = flat_n;

  if (r <= 0.0f) {
    out->state = AD_STATE_OK;
    out->kind = AD_DAMAGE_NONE;
  } else if (r >= 1.0f) {
    out->state = AD_STATE_BAD;
  } else {
    out->state = AD_STATE_REPAIR;
  }
}
