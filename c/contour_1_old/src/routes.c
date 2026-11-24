#include "adaptive.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static void ad_build_gamma_lut(float gamma, uint8_t* lut) {
  int i;
  float g;
  if (gamma < 0.05f) {
    gamma = 0.05f;
  }
  for (i = 0; i < 256; i += 1) {
    g = powf((float)i / 255.0f, gamma);
    if (g < 0.0f) {
      g = 0.0f;
    }
    if (g > 1.0f) {
      g = 1.0f;
    }
    lut[i] = (uint8_t)(g * 255.0f + 0.5f);
  }
}

static void ad_build_deover_lut(float r, uint8_t* lut) {
  int i;
  float pivot;
  float ceiling;
  float amount;
  float lift;
  if (r < 0.0f) {
    r = 0.0f;
  }
  if (r > 1.0f) {
    r = 1.0f;
  }
  pivot = 0.52f - 0.14f * r;
  ceiling = 0.88f - 0.28f * r;
  amount = 1.2f + 1.8f * r;
  lift = 0.35f + 0.45f * r;
  for (i = 0; i < 256; i += 1) {
    float x = (float)i / 255.0f;
    float y;
    if (x <= pivot) {
      float t = (pivot <= 1.0e-6f) ? 0.0f : (x / pivot);
      y = pivot * powf(t, 1.0f / (1.0f + lift));
    } else {
      float t = (x - pivot) / (1.0f - pivot);
      float soft = 1.0f - powf(1.0f - t, amount);
      y = pivot + soft * (ceiling - pivot);
    }
    if (y < 0.0f) {
      y = 0.0f;
    }
    if (y > 1.0f) {
      y = 1.0f;
    }
    lut[i] = (uint8_t)(y * 255.0f + 0.5f);
  }
}

static void ad_apply_lut(AdFrame* frame, const uint8_t* lut) {
  uint32_t y;
  uint32_t x;
  uint8_t* row;
  for (y = 0; y < frame->height; y += 1) {
    row = frame->data + y * (uint32_t)frame->stride;
    for (x = 0; x < frame->width; x += 1) {
      row[x] = lut[row[x]];
    }
  }
}

static void ad_percentile_bounds(const uint32_t* hist, uint32_t n, float lo_p, float hi_p, int* lo, int* hi) {
  uint32_t target_lo;
  uint32_t target_hi;
  uint32_t acc;
  int i;
  *lo = 0;
  *hi = 255;
  if (n == 0) {
    return;
  }
  target_lo = (uint32_t)(lo_p * (float)n);
  target_hi = (uint32_t)(hi_p * (float)n);
  if (target_hi >= n) {
    target_hi = n - 1;
  }
  acc = 0;
  for (i = 0; i < 256; i += 1) {
    acc += hist[i];
    if (acc > target_lo) {
      *lo = i;
      break;
    }
  }
  acc = 0;
  for (i = 0; i < 256; i += 1) {
    acc += hist[i];
    if (acc > target_hi) {
      *hi = i;
      break;
    }
  }
  if (*hi <= *lo) {
    *hi = *lo + 1;
    if (*hi > 255) {
      *hi = 255;
      if (*lo > 0) {
        *lo = *hi - 1;
      }
    }
  }
}

static void ad_build_stretch_lut(const AdAssess* assess, uint8_t* lut) {
  int lo;
  int hi;
  int i;
  float scale;
  float v;
  ad_percentile_bounds(assess->hist, assess->sample_count, 0.01f, 0.99f, &lo, &hi);
  scale = 255.0f / (float)(hi - lo);
  for (i = 0; i < 256; i += 1) {
    if (i <= lo) {
      lut[i] = 0;
    } else if (i >= hi) {
      lut[i] = 255;
    } else {
      v = ((float)(i - lo)) * scale;
      if (v < 0.0f) {
        v = 0.0f;
      }
      if (v > 255.0f) {
        v = 255.0f;
      }
      lut[i] = (uint8_t)(v + 0.5f);
    }
  }
}

static void ad_clahe_tile_lut(const uint32_t* hist, uint32_t n, float clip_limit, uint8_t* lut) {
  uint32_t clipped[256];
  uint32_t i;
  uint32_t excess;
  uint32_t limit;
  uint32_t bonus;
  uint32_t rem;
  uint32_t cdf;
  uint32_t cdf_min;
  float scale;

  if (n == 0) {
    for (i = 0; i < 256; i += 1) {
      lut[i] = (uint8_t)i;
    }
    return;
  }

  limit = (uint32_t)(clip_limit * ((float)n / 256.0f) + 0.5f);
  if (limit < 1) {
    limit = 1;
  }

  excess = 0;
  for (i = 0; i < 256; i += 1) {
    if (hist[i] > limit) {
      excess += hist[i] - limit;
      clipped[i] = limit;
    } else {
      clipped[i] = hist[i];
    }
  }

  bonus = excess / 256;
  rem = excess % 256;
  for (i = 0; i < 256; i += 1) {
    clipped[i] += bonus;
    if (i < rem) {
      clipped[i] += 1;
    }
  }

  cdf = 0;
  cdf_min = 0;
  for (i = 0; i < 256; i += 1) {
    if (clipped[i] != 0) {
      cdf_min = clipped[i];
      break;
    }
  }
  scale = 255.0f / (float)(n - cdf_min);
  for (i = 0; i < 256; i += 1) {
    cdf += clipped[i];
    if (cdf <= cdf_min) {
      lut[i] = 0;
    } else {
      float val = (float)(cdf - cdf_min) * scale;
      if (val < 0.0f) {
        val = 0.0f;
      }
      if (val > 255.0f) {
        val = 255.0f;
      }
      lut[i] = (uint8_t)(val + 0.5f);
    }
  }
}

static void ad_apply_clahe(AdFrame* frame, float clip_limit, uint8_t tiles_x, uint8_t tiles_y) {
  uint8_t tx;
  uint8_t ty;
  uint16_t tile_w;
  uint16_t tile_h;
  uint32_t hist[256];
  uint8_t luts[16][16][256];
  uint32_t x;
  uint32_t y;
  uint32_t i;
  uint8_t* src;
  uint8_t* dst_buf;
  uint32_t bytes;

  if (tiles_x < 2) {
    tiles_x = 2;
  }
  if (tiles_y < 2) {
    tiles_y = 2;
  }
  if (tiles_x > 16) {
    tiles_x = 16;
  }
  if (tiles_y > 16) {
    tiles_y = 16;
  }

  tile_w = (uint16_t)((frame->width + tiles_x - 1) / tiles_x);
  tile_h = (uint16_t)((frame->height + tiles_y - 1) / tiles_y);
  if (tile_w == 0 || tile_h == 0) {
    return;
  }

  for (ty = 0; ty < tiles_y; ty += 1) {
    uint32_t y0 = (uint32_t)ty * (uint32_t)tile_h;
    uint32_t y1 = y0 + tile_h;
    if (y1 > frame->height) {
      y1 = frame->height;
    }
    for (tx = 0; tx < tiles_x; tx += 1) {
      uint32_t x0 = (uint32_t)tx * (uint32_t)tile_w;
      uint32_t x1 = x0 + tile_w;
      uint32_t count = 0;
      if (x1 > frame->width) {
        x1 = frame->width;
      }
      for (i = 0; i < 256; i += 1) {
        hist[i] = 0;
      }
      for (y = y0; y < y1; y += 1) {
        src = frame->data + y * (uint32_t)frame->stride;
        for (x = x0; x < x1; x += 1) {
          hist[src[x]] += 1;
          count += 1;
        }
      }
      ad_clahe_tile_lut(hist, count, clip_limit, luts[ty][tx]);
    }
  }

  bytes = (uint32_t)frame->height * (uint32_t)frame->stride;
  dst_buf = (uint8_t*)malloc(bytes);
  if (dst_buf == 0) {
    return;
  }
  memcpy(dst_buf, frame->data, bytes);

  for (y = 0; y < frame->height; y += 1) {
    float gy = ((float)y + 0.5f) / (float)tile_h - 0.5f;
    int ty0 = (int)floorf(gy);
    int ty1 = ty0 + 1;
    float fy = gy - (float)ty0;
    if (ty0 < 0) {
      ty0 = 0;
      ty1 = 0;
      fy = 0.0f;
    }
    if (ty1 >= tiles_y) {
      ty1 = tiles_y - 1;
      ty0 = ty1;
      fy = 0.0f;
    }
    src = frame->data + y * (uint32_t)frame->stride;
    for (x = 0; x < frame->width; x += 1) {
      float gx = ((float)x + 0.5f) / (float)tile_w - 0.5f;
      int tx0 = (int)floorf(gx);
      int tx1 = tx0 + 1;
      float fx = gx - (float)tx0;
      uint8_t p = src[x];
      float v00;
      float v10;
      float v01;
      float v11;
      float v;
      if (tx0 < 0) {
        tx0 = 0;
        tx1 = 0;
        fx = 0.0f;
      }
      if (tx1 >= tiles_x) {
        tx1 = tiles_x - 1;
        tx0 = tx1;
        fx = 0.0f;
      }
      v00 = (float)luts[ty0][tx0][p];
      v10 = (float)luts[ty0][tx1][p];
      v01 = (float)luts[ty1][tx0][p];
      v11 = (float)luts[ty1][tx1][p];
      v = (1.0f - fy) * ((1.0f - fx) * v00 + fx * v10) + fy * ((1.0f - fx) * v01 + fx * v11);
      if (v < 0.0f) {
        v = 0.0f;
      }
      if (v > 255.0f) {
        v = 255.0f;
      }
      dst_buf[y * (uint32_t)frame->stride + x] = (uint8_t)(v + 0.5f);
    }
  }

  memcpy(frame->data, dst_buf, bytes);
  free(dst_buf);
}

static void ad_box3_blur(const AdFrame* src, uint8_t* dst) {
  uint32_t y;
  uint32_t x;
  int dy;
  int dx;
  for (y = 0; y < src->height; y += 1) {
    for (x = 0; x < src->width; x += 1) {
      int sum = 0;
      int count = 0;
      for (dy = -1; dy <= 1; dy += 1) {
        int yy = (int)y + dy;
        if (yy < 0 || yy >= (int)src->height) {
          continue;
        }
        for (dx = -1; dx <= 1; dx += 1) {
          int xx = (int)x + dx;
          if (xx < 0 || xx >= (int)src->width) {
            continue;
          }
          sum += src->data[(uint32_t)yy * (uint32_t)src->stride + (uint32_t)xx];
          count += 1;
        }
      }
      if (count <= 0) {
        dst[y * (uint32_t)src->stride + x] = src->data[y * (uint32_t)src->stride + x];
      } else {
        dst[y * (uint32_t)src->stride + x] = (uint8_t)((sum + count / 2) / count);
      }
    }
  }
}

static void ad_apply_denoise3(AdFrame* frame) {
  uint32_t bytes;
  uint8_t* tmp;
  if (frame->width < 2 || frame->height < 2) {
    return;
  }
  bytes = (uint32_t)frame->height * (uint32_t)frame->stride;
  tmp = (uint8_t*)malloc(bytes);
  if (tmp == 0) {
    return;
  }
  ad_box3_blur(frame, tmp);
  memcpy(frame->data, tmp, bytes);
  free(tmp);
}

static void ad_apply_unsharp(AdFrame* frame, float amount) {
  uint32_t bytes;
  uint8_t* blur;
  uint32_t y;
  uint32_t x;
  if (frame->width < 2 || frame->height < 2) {
    return;
  }
  if (amount < 0.0f) {
    amount = 0.0f;
  }
  if (amount > 3.0f) {
    amount = 3.0f;
  }
  bytes = (uint32_t)frame->height * (uint32_t)frame->stride;
  blur = (uint8_t*)malloc(bytes);
  if (blur == 0) {
    return;
  }
  ad_box3_blur(frame, blur);
  for (y = 0; y < frame->height; y += 1) {
    for (x = 0; x < frame->width; x += 1) {
      uint32_t idx = y * (uint32_t)frame->stride + x;
      float orig = (float)frame->data[idx];
      float b = (float)blur[idx];
      float v = orig + amount * (orig - b);
      if (v < 0.0f) {
        v = 0.0f;
      }
      if (v > 255.0f) {
        v = 255.0f;
      }
      frame->data[idx] = (uint8_t)(v + 0.5f);
    }
  }
  free(blur);
}

void ad_apply_route(AdFrame* frame, const AdDecision* decision, const AdConfig* cfg) {
  uint8_t lut[256];
  if (frame == 0 || decision == 0 || cfg == 0 || frame->data == 0) {
    return;
  }
  if (decision->route == AD_ROUTE_NONE) {
    return;
  }
  if (decision->route == AD_ROUTE_GAMMA_LIGHT) {
    ad_build_gamma_lut(decision->gamma, lut);
    ad_apply_lut(frame, lut);
    return;
  }
  if (decision->route == AD_ROUTE_GAMMA_DARK) {
    ad_build_deover_lut(decision->r, lut);
    ad_apply_lut(frame, lut);
    return;
  }
  if (decision->route == AD_ROUTE_STRETCH) {
    ad_build_stretch_lut(&decision->assess, lut);
    ad_apply_lut(frame, lut);
    return;
  }
  if (decision->route == AD_ROUTE_CLAHE) {
    ad_apply_clahe(frame, decision->clahe_clip, cfg->clahe_tiles_x, cfg->clahe_tiles_y);
    return;
  }
  if (decision->route == AD_ROUTE_DENOISE) {
    ad_apply_denoise3(frame);
    return;
  }
  if (decision->route == AD_ROUTE_SHARPEN) {
    ad_apply_unsharp(frame, decision->sharpen_amount);
  }
}
