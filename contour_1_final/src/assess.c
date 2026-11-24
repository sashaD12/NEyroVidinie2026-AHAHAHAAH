#include "adaptive.h"

#include <math.h>

static float ad_clamp01(float x) {
  if (x < 0.0f) {
    return 0.0f;
  }
  if (x > 1.0f) {
    return 1.0f;
  }
  return x;
}

static float ad_max3(float a, float b, float c) {
  float m = a;
  if (b > m) {
    m = b;
  }
  if (c > m) {
    m = c;
  }
  return m;
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

static float ad_flat_residual(
  const uint16_t* grad,
  const float* resid,
  uint32_t count,
  float frac,
  uint32_t* used
) {
  uint32_t hist[AD_GRAD_BINS];
  uint32_t i;
  uint32_t k;
  uint32_t cum;
  uint32_t need;
  uint32_t taken;
  uint32_t g_star;
  double sum;

  *used = 0;
  if (count == 0) {
    return 0.0f;
  }
  k = (uint32_t)(frac * (float)count + 0.5f);
  if (k < 1) {
    k = 1;
  }
  if (k > count) {
    k = count;
  }

  for (i = 0; i < AD_GRAD_BINS; i += 1) {
    hist[i] = 0;
  }
  for (i = 0; i < count; i += 1) {
    hist[grad[i]] += 1;
  }

  cum = 0;
  need = 0;
  g_star = AD_GRAD_BINS - 1;
  for (i = 0; i < AD_GRAD_BINS; i += 1) {
    if (cum + hist[i] >= k) {
      g_star = i;
      need = k - cum;
      break;
    }
    cum += hist[i];
  }

  sum = 0.0;
  taken = 0;
  for (i = 0; i < count; i += 1) {
    if (grad[i] < g_star) {
      sum += (double)resid[i];
    } else if (grad[i] == g_star && taken < need) {
      sum += (double)resid[i];
      taken += 1;
    }
  }

  *used = k;
  return (float)(sum / (double)k);
}

static float ad_block_sharpness(const AdFrame* frame, float step_x, float step_y, float noise_sigma) {
  static float block[AD_ASSESS_H][AD_ASSESS_W];
  int32_t bw;
  int32_t bh;
  uint16_t sx;
  uint16_t sy;
  double sum;
  double sum_sq;
  double lap_sum;
  double lap_sum_sq;
  double var_b;
  double var_l;
  double noise_l;
  uint32_t lap_n;
  uint32_t n;

  bw = (int32_t)step_x;
  bh = (int32_t)step_y;
  if (bw > 4) {
    bw = 4;
  }
  if (bh > 4) {
    bh = 4;
  }
  if (bw < 1) {
    bw = 1;
  }
  if (bh < 1) {
    bh = 1;
  }

  sum = 0.0;
  sum_sq = 0.0;
  n = 0;
  for (sy = 0; sy < AD_ASSESS_H; sy += 1) {
    int32_t y0 = (int32_t)((float)sy * step_y);
    if (y0 >= (int32_t)frame->height) {
      y0 = (int32_t)frame->height - 1;
    }
    for (sx = 0; sx < AD_ASSESS_W; sx += 1) {
      int32_t x0 = (int32_t)((float)sx * step_x);
      int32_t yy;
      int32_t xx;
      int32_t acc = 0;
      int32_t cnt = 0;
      float m;
      if (x0 >= (int32_t)frame->width) {
        x0 = (int32_t)frame->width - 1;
      }
      for (yy = y0; yy < y0 + bh && yy < (int32_t)frame->height; yy += 1) {
        const uint8_t* row = frame->data + (uint32_t)yy * (uint32_t)frame->stride;
        for (xx = x0; xx < x0 + bw && xx < (int32_t)frame->width; xx += 1) {
          acc += (int32_t)row[xx];
          cnt += 1;
        }
      }
      m = (float)acc / (float)cnt;
      block[sy][sx] = m;
      sum += (double)m;
      sum_sq += (double)m * (double)m;
      n += 1;
    }
  }

  lap_sum = 0.0;
  lap_sum_sq = 0.0;
  lap_n = 0;
  for (sy = 1; sy + 1 < AD_ASSESS_H; sy += 1) {
    for (sx = 1; sx + 1 < AD_ASSESS_W; sx += 1) {
      double L = (double)block[sy][sx + 1]
        + (double)block[sy][sx - 1]
        + (double)block[sy + 1][sx]
        + (double)block[sy - 1][sx]
        - 4.0 * (double)block[sy][sx];
      lap_sum += L;
      lap_sum_sq += L * L;
      lap_n += 1;
    }
  }
  if (n == 0 || lap_n == 0) {
    return 0.0f;
  }

  var_b = sum_sq / (double)n - (sum / (double)n) * (sum / (double)n);
  var_l = lap_sum_sq / (double)lap_n - (lap_sum / (double)lap_n) * (lap_sum / (double)lap_n);
  noise_l = 20.0 * (double)noise_sigma * (double)noise_sigma / (double)(bw * bh);
  var_l -= noise_l;
  if (var_l < 0.0) {
    var_l = 0.0;
  }
  if (var_b < 1.0) {
    var_b = 1.0;
  }
  return (float)(var_l / var_b);
}

static void ad_log_kind(
  AdAssess* out,
  const AdConfig* cfg,
  float d_u,
  float d_o,
  float d_c,
  float d_n,
  float d_b,
  float d_iso,
  float d_motion,
  float pdark
) {
  float d_l;
  float r_light;
  float r_n;
  float r_b;
  float r;
  float best;
  AdDamageKind kind;
  AdDamageKind light_kind;

  d_l = ad_max3(d_u, d_o, d_c);
  light_kind = AD_DAMAGE_NONE;
  if ((d_u >= cfg->tau_l && d_o >= cfg->tau_l) || (out->ps >= 0.12f && pdark >= 0.12f)) {
    light_kind = AD_DAMAGE_MIXED;
    d_l = fmaxf(d_u, d_o);
    if (d_l < cfg->tau_l) {
      d_l = cfg->tau_l + 0.05f;
    }
  } else if (d_u >= cfg->tau_l && d_u >= d_o) {
    light_kind = AD_DAMAGE_UNDER;
    d_l = fmaxf(d_u, d_c);
  } else if (d_o >= cfg->tau_l && d_o >= d_u) {
    light_kind = AD_DAMAGE_OVER;
    d_l = fmaxf(d_o, d_c);
  } else if (d_c >= cfg->tau_l) {
    light_kind = AD_DAMAGE_CONTRAST;
    d_l = d_c;
  } else if (d_l > 0.0f) {
    if (d_u >= d_o && d_u >= d_c) {
      light_kind = AD_DAMAGE_UNDER;
    } else if (d_o >= d_u && d_o >= d_c) {
      light_kind = AD_DAMAGE_OVER;
    } else {
      light_kind = AD_DAMAGE_CONTRAST;
    }
  }

  r_light = ad_severity_r(d_l, cfg->tau_l, cfg->t_l);
  r_n = ad_severity_r(d_n, cfg->tau_n, cfg->t_n);
  r_b = ad_severity_r(d_b, cfg->tau_b, cfg->t_b);

  kind = AD_DAMAGE_NONE;
  r = 0.0f;
  best = 0.0f;
  if (d_b >= cfg->tau_b && r_b >= best) {
    kind = AD_DAMAGE_BLUR;
    r = r_b;
    best = r_b;
  }
  if (d_n >= cfg->tau_n && r_n > best) {
    kind = AD_DAMAGE_NOISE;
    r = r_n;
    best = r_n;
  }
  if (r_light > best) {
    kind = light_kind;
    r = r_light;
  }

  out->log_kind = kind;
  out->log_r = r;
  if (r <= 0.0f || kind == AD_DAMAGE_NONE) {
    out->log_state = AD_STATE_OK;
    out->log_kind = AD_DAMAGE_NONE;
    out->log_r = 0.0f;
  } else if (r >= 1.0f && kind == AD_DAMAGE_BLUR && d_motion >= d_iso) {
    out->log_state = AD_STATE_REPAIR;
    out->log_r = 0.92f;
  } else if (r >= 1.0f && (kind == AD_DAMAGE_BLUR || kind == AD_DAMAGE_NOISE)) {
    out->log_state = AD_STATE_BAD;
  } else if (r >= 1.0f) {
    out->log_state = AD_STATE_REPAIR;
    out->log_r = 0.99f;
  } else {
    out->log_state = AD_STATE_REPAIR;
  }
}

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out) {
  uint32_t i;
  uint32_t n;
  double sum;
  double sum_sq;
  float mu;
  float sigma;
  float pb;
  float ps;
  float pdark;
  float d_u;
  float d_o;
  float d_c;
  float step_x;
  float step_y;
  uint16_t sx;
  uint16_t sy;
  uint16_t x;
  uint16_t y;
  uint8_t v;
  uint32_t lap_n;
  uint32_t grad_n;
  uint32_t flat_used;
  double lap_sum;
  double lap_sum_sq;
  double ex_sum;
  double ey_sum;
  float s_L;
  float n_flat;
  float d_n;
  float d_b;
  float d_iso;
  float d_motion;
  float aniso;
  float ex_mean;
  float ey_mean;
  float e_min;
  float e_max;
  float s_L_raw;
  float noise_sigma;
  double imm_sum;
  uint8_t grid[AD_ASSESS_H][AD_ASSESS_W];
  uint16_t grad_buf[AD_ASSESS_H * AD_ASSESS_W];
  float resid_buf[AD_ASSESS_H * AD_ASSESS_W];

  if (out == 0) {
    return;
  }

  for (i = 0; i < AD_HIST_BINS; i += 1) {
    out->hist[i] = 0;
  }
  for (i = 0; i < AD_VEC_DIM; i += 1) {
    out->v[i] = 0.0f;
  }
  out->mu = 0.0f;
  out->sigma = 0.0f;
  out->pb = 0.0f;
  out->ps = 0.0f;
  out->s_L = 0.0f;
  out->s_L_raw = 0.0f;
  out->noise_sigma = 0.0f;
  out->n_flat = 0.0f;
  out->aniso = 1.0f;
  out->e_max = 0.0f;
  out->d_motion = 0.0f;
  out->sample_count = 0;
  out->flat_count = 0;
  out->log_kind = AD_DAMAGE_NONE;
  out->log_state = AD_STATE_OK;
  out->log_r = 0.0f;

  if (frame == 0 || cfg == 0 || frame->data == 0 || frame->width == 0 || frame->height == 0) {
    return;
  }

  step_x = (float)frame->width / (float)AD_ASSESS_W;
  step_y = (float)frame->height / (float)AD_ASSESS_H;
  if (step_x < 1.0f) {
    step_x = 1.0f;
  }
  if (step_y < 1.0f) {
    step_y = 1.0f;
  }

  for (sy = 0; sy < AD_ASSESS_H; sy += 1) {
    y = (uint16_t)((float)sy * step_y);
    if (y >= frame->height) {
      y = (uint16_t)(frame->height - 1);
    }
    for (sx = 0; sx < AD_ASSESS_W; sx += 1) {
      x = (uint16_t)((float)sx * step_x);
      if (x >= frame->width) {
        x = (uint16_t)(frame->width - 1);
      }
      v = frame->data[(uint32_t)y * (uint32_t)frame->stride + (uint32_t)x];
      grid[sy][sx] = v;
      out->hist[v] += 1;
      out->sample_count += 1;
    }
  }

  n = out->sample_count;
  if (n == 0) {
    return;
  }

  sum = 0.0;
  sum_sq = 0.0;
  for (i = 0; i < AD_HIST_BINS; i += 1) {
    sum += (double)i * (double)out->hist[i];
    sum_sq += (double)i * (double)i * (double)out->hist[i];
  }
  mu = (float)(sum / (double)n);
  sigma = (float)sqrt((sum_sq / (double)n) - ((double)mu * (double)mu));
  if (sigma < 0.0f) {
    sigma = 0.0f;
  }

  pb = 0.0f;
  ps = 0.0f;
  pdark = 0.0f;
  for (i = 0; i <= 10; i += 1) {
    pb += (float)out->hist[i];
  }
  for (i = 245; i < AD_HIST_BINS; i += 1) {
    ps += (float)out->hist[i];
  }
  for (i = 0; i <= 55; i += 1) {
    pdark += (float)out->hist[i];
  }
  pb /= (float)n;
  ps /= (float)n;
  pdark /= (float)n;

  d_u = ad_clamp01(fmaxf((cfg->mu0 - mu) / cfg->mu0, fmaxf(pb / cfg->pmax, pdark / 0.75f)));
  d_o = ad_clamp01(fmaxf((mu - cfg->mu1) / (255.0f - cfg->mu1), ps / cfg->pmax));
  d_c = ad_clamp01(1.0f - (sigma / cfg->sigma0));

  lap_n = 0;
  grad_n = 0;
  lap_sum = 0.0;
  lap_sum_sq = 0.0;
  ex_sum = 0.0;
  ey_sum = 0.0;

  for (sy = 1; sy + 1 < AD_ASSESS_H; sy += 1) {
    for (sx = 1; sx + 1 < AD_ASSESS_W; sx += 1) {
      int32_t c;
      int32_t L;
      float Lf;

      c = (int32_t)grid[sy][sx];
      L = (int32_t)grid[sy][sx + 1]
        + (int32_t)grid[sy][sx - 1]
        + (int32_t)grid[sy + 1][sx]
        + (int32_t)grid[sy - 1][sx]
        - 4 * c;
      Lf = (float)L;
      lap_sum += (double)Lf;
      lap_sum_sq += (double)Lf * (double)Lf;
      lap_n += 1;
    }
  }

  imm_sum = 0.0;
  if (frame->width >= 3 && frame->height >= 3) {
    for (sy = 0; sy < AD_ASSESS_H; sy += 1) {
      int32_t fy = (int32_t)((float)sy * step_y);
      if (fy < 1) {
        fy = 1;
      }
      if (fy + 1 >= (int32_t)frame->height) {
        fy = (int32_t)frame->height - 2;
      }
      for (sx = 0; sx < AD_ASSESS_W; sx += 1) {
        int32_t fx = (int32_t)((float)sx * step_x);
        int32_t p[3][3];
        int32_t sum3;
        int32_t gx;
        int32_t gy;
        int32_t imm;
        uint8_t yy;
        uint8_t xx;

        if (fx < 1) {
          fx = 1;
        }
        if (fx + 1 >= (int32_t)frame->width) {
          fx = (int32_t)frame->width - 2;
        }

        sum3 = 0;
        for (yy = 0; yy < 3; yy += 1) {
          for (xx = 0; xx < 3; xx += 1) {
            p[yy][xx] = (int32_t)ad_sample(frame, fx + (int32_t)xx - 1, fy + (int32_t)yy - 1);
            sum3 += p[yy][xx];
          }
        }
        gx = ad_iabs(p[1][2] - p[1][0]);
        gy = ad_iabs(p[2][1] - p[0][1]);
        ex_sum += (double)gx;
        ey_sum += (double)gy;
        imm = (p[0][0] + p[0][2] + p[2][0] + p[2][2])
          - 2 * (p[0][1] + p[2][1] + p[1][0] + p[1][2])
          + 4 * p[1][1];
        imm_sum += (double)ad_iabs(imm);
        grad_buf[grad_n] = (uint16_t)(gx + gy);
        resid_buf[grad_n] = fabsf((float)p[1][1] - (float)sum3 / 9.0f);
        grad_n += 1;
      }
    }
  }

  s_L_raw = 0.0f;
  if (lap_n > 0) {
    double mean_L = lap_sum / (double)lap_n;
    double var_L = (lap_sum_sq / (double)lap_n) - (mean_L * mean_L);
    if (var_L < 0.0) {
      var_L = 0.0;
    }
    s_L_raw = (float)var_L;
  }

  noise_sigma = 0.0f;
  if (grad_n > 0) {
    noise_sigma = (float)(1.2533141 / 6.0 * imm_sum / (double)grad_n);
  }
  s_L = ad_block_sharpness(frame, step_x, step_y, noise_sigma);

  n_flat = ad_flat_residual(grad_buf, resid_buf, grad_n, cfg->flat_frac, &flat_used);

  ex_mean = 0.0f;
  ey_mean = 0.0f;
  e_max = 0.0f;
  aniso = 1.0f;
  if (grad_n > 0) {
    ex_mean = (float)(ex_sum / (double)grad_n);
    ey_mean = (float)(ey_sum / (double)grad_n);
    e_min = fminf(ex_mean, ey_mean);
    e_max = fmaxf(ex_mean, ey_mean);
    if (e_min < 0.5f) {
      e_min = 0.5f;
    }
    aniso = e_max / e_min;
  }

  if (cfg->s_L0 > 0.0f) {
    d_iso = ad_clamp01(1.0f - (log1pf(s_L) / log1pf(cfg->s_L0)));
  } else {
    d_iso = 0.0f;
  }

  d_motion = 0.0f;
  if (aniso > 1.45f && e_max > 1.8f) {
    d_motion = ad_clamp01((aniso - 1.45f) / 1.55f);
  }

  d_b = fmaxf(d_iso, d_motion);

  d_n = 0.0f;
  if (flat_used > 0 && cfg->n0 > 0.0f) {
    d_n = ad_clamp01((n_flat - 1.35f) / cfg->n0);
  }
  if (d_motion >= 0.35f) {
    d_n *= 0.25f;
  }
  if (s_L_raw > 8000.0f) {
    d_n *= ad_clamp01(12000.0f / s_L_raw);
  }

  out->v[AD_V_U] = d_u;
  out->v[AD_V_O] = d_o;
  out->v[AD_V_C] = d_c;
  out->v[AD_V_N] = d_n;
  out->v[AD_V_B] = d_b;
  out->mu = mu;
  out->sigma = sigma;
  out->pb = pb;
  out->ps = ps;
  out->s_L = s_L;
  out->s_L_raw = s_L_raw;
  out->noise_sigma = noise_sigma;
  out->n_flat = n_flat;
  out->aniso = aniso;
  out->e_max = e_max;
  out->d_motion = d_motion;
  out->flat_count = flat_used;

  ad_log_kind(out, cfg, d_u, d_o, d_c, d_n, d_b, d_iso, d_motion, pdark);
}
