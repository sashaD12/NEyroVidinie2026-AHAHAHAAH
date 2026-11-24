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

void ad_assess_frame(const AdFrame* frame, const AdConfig* cfg, AdAssess* out) {
  uint32_t i;
  uint32_t n;
  double sum;
  double sum_sq;
  float mu;
  float sigma;
  float pb;
  float ps;
  float d_u;
  float d_o;
  float d_c;
  float d_l;
  float r;
  float step_x;
  float step_y;
  uint16_t sx;
  uint16_t sy;
  uint16_t x;
  uint16_t y;
  uint8_t v;
  AdDamageKind kind;

  if (out == 0) {
    return;
  }

  for (i = 0; i < AD_HIST_BINS; i += 1) {
    out->hist[i] = 0;
  }
  out->mu = 0.0f;
  out->sigma = 0.0f;
  out->pb = 0.0f;
  out->ps = 0.0f;
  out->d_u = 0.0f;
  out->d_o = 0.0f;
  out->d_c = 0.0f;
  out->d_l = 0.0f;
  out->r = 0.0f;
  out->kind = AD_DAMAGE_NONE;
  out->state = AD_STATE_OK;
  out->sample_count = 0;

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
  for (i = 0; i <= 10; i += 1) {
    pb += (float)out->hist[i];
  }
  for (i = 245; i < AD_HIST_BINS; i += 1) {
    ps += (float)out->hist[i];
  }
  pb /= (float)n;
  ps /= (float)n;

  {
    float pdark = 0.0f;
    for (i = 0; i <= 55; i += 1) {
      pdark += (float)out->hist[i];
    }
    pdark /= (float)n;
    d_u = ad_clamp01(fmaxf((cfg->mu0 - mu) / cfg->mu0, fmaxf(pb / cfg->pmax, pdark / 0.75f)));
    d_o = ad_clamp01(fmaxf((mu - cfg->mu1) / (255.0f - cfg->mu1), ps / cfg->pmax));
    d_c = ad_clamp01(1.0f - (sigma / cfg->sigma0));
    d_l = ad_max3(d_u, d_o, d_c);

    kind = AD_DAMAGE_NONE;
    if ((d_u >= cfg->tau_l && d_o >= cfg->tau_l) || (ps >= 0.12f && pdark >= 0.12f)) {
      kind = AD_DAMAGE_MIXED;
      d_l = fmaxf(d_u, d_o);
      if (d_l < cfg->tau_l) {
        d_l = cfg->tau_l + 0.05f;
      }
    } else if (d_u >= cfg->tau_l && d_u >= d_o) {
      kind = AD_DAMAGE_UNDER;
      d_l = fmaxf(d_u, d_c);
    } else if (d_o >= cfg->tau_l && d_o >= d_u) {
      kind = AD_DAMAGE_OVER;
      d_l = fmaxf(d_o, d_c);
    } else if (d_c >= cfg->tau_l) {
      kind = AD_DAMAGE_CONTRAST;
      d_l = d_c;
    } else if (d_l > 0.0f) {
      if (d_u >= d_o && d_u >= d_c) {
        kind = AD_DAMAGE_UNDER;
      } else if (d_o >= d_u && d_o >= d_c) {
        kind = AD_DAMAGE_OVER;
      } else {
        kind = AD_DAMAGE_CONTRAST;
      }
    }
  }

  if (d_l <= cfg->tau_l) {
    r = 0.0f;
  } else if (d_l >= cfg->t_l) {
    r = 1.0f;
  } else {
    r = (d_l - cfg->tau_l) / (cfg->t_l - cfg->tau_l);
  }

  out->mu = mu;
  out->sigma = sigma;
  out->pb = pb;
  out->ps = ps;
  out->d_u = d_u;
  out->d_o = d_o;
  out->d_c = d_c;
  out->d_l = d_l;
  out->r = r;
  out->kind = kind;

  if (r <= 0.0f) {
    out->state = AD_STATE_OK;
    out->kind = AD_DAMAGE_NONE;
  } else if (r >= 1.0f) {
    out->state = AD_STATE_BAD;
  } else {
    out->state = AD_STATE_REPAIR;
  }
}
