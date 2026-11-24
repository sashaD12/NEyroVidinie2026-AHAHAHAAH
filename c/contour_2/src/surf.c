#include "adaptive.h"

#include <stdlib.h>

static int32_t ad_ii_at(const int32_t* ii, int32_t ii_w, int32_t x, int32_t y) {
  if (x < 0) {
    x = 0;
  }
  if (y < 0) {
    y = 0;
  }
  return ii[(uint32_t)y * (uint32_t)ii_w + (uint32_t)x];
}

static int32_t ad_box_sum(
  const int32_t* ii,
  int32_t ii_w,
  int32_t x0,
  int32_t y0,
  int32_t x1,
  int32_t y1
) {
  int32_t a;
  int32_t b;
  int32_t c;
  int32_t d;
  if (x1 < x0 || y1 < y0) {
    return 0;
  }
  a = ad_ii_at(ii, ii_w, x0, y0);
  b = ad_ii_at(ii, ii_w, x1 + 1, y0);
  c = ad_ii_at(ii, ii_w, x0, y1 + 1);
  d = ad_ii_at(ii, ii_w, x1 + 1, y1 + 1);
  return d - b - c + a;
}

static void ad_build_integral(const AdFrame* frame, int32_t* ii, int32_t ii_w) {
  int32_t y;
  int32_t x;
  int32_t ii_h = (int32_t)frame->height + 1;
  for (x = 0; x < ii_w; x += 1) {
    ii[x] = 0;
  }
  for (y = 1; y < ii_h; y += 1) {
    ii[(uint32_t)y * (uint32_t)ii_w] = 0;
  }
  for (y = 0; y < (int32_t)frame->height; y += 1) {
    int32_t row_sum = 0;
    for (x = 0; x < (int32_t)frame->width; x += 1) {
      row_sum += (int32_t)frame->data[(uint32_t)y * (uint32_t)frame->stride + (uint32_t)x];
      ii[(uint32_t)(y + 1) * (uint32_t)ii_w + (uint32_t)(x + 1)] =
        ii[(uint32_t)y * (uint32_t)ii_w + (uint32_t)(x + 1)] + row_sum;
    }
  }
}

static float ad_hessian_response(
  const int32_t* ii,
  int32_t ii_w,
  int32_t x,
  int32_t y,
  int32_t lobe
) {
  float dxx;
  float dyy;
  float dxy;
  float det;
  int32_t area;
  int32_t l = lobe;
  int32_t l2 = lobe * 2;
  int32_t l3 = lobe * 3;

  dxx = (float)(
    ad_box_sum(ii, ii_w, x - l3, y - l, x + l3, y + l)
    - 3 * ad_box_sum(ii, ii_w, x - l, y - l, x + l, y + l)
  );
  dyy = (float)(
    ad_box_sum(ii, ii_w, x - l, y - l3, x + l, y + l3)
    - 3 * ad_box_sum(ii, ii_w, x - l, y - l, x + l, y + l)
  );
  dxy = (float)(
    ad_box_sum(ii, ii_w, x + 1, y - l2, x + l2, y - 1)
    + ad_box_sum(ii, ii_w, x - l2, y + 1, x - 1, y + l2)
    - ad_box_sum(ii, ii_w, x - l2, y - l2, x - 1, y - 1)
    - ad_box_sum(ii, ii_w, x + 1, y + 1, x + l2, y + l2)
  );

  area = (2 * l3 + 1) * (2 * l + 1);
  if (area < 1) {
    area = 1;
  }
  dxx /= (float)area;
  dyy /= (float)area;
  dxy /= (float)area;

  det = dxx * dyy - (0.9f * dxy) * (0.9f * dxy);
  if (det < 0.0f) {
    return -det;
  }
  return det;
}

static void ad_insert_topk(
  AdSurfKeypoint* heap,
  uint16_t* count,
  uint16_t max_out,
  float x,
  float y,
  float scale,
  float response
) {
  uint16_t i;
  uint16_t worst = 0;

  if (*count < max_out) {
    heap[*count].x = x;
    heap[*count].y = y;
    heap[*count].scale = scale;
    heap[*count].response = response;
    *count = (uint16_t)(*count + 1);
    return;
  }

  for (i = 1; i < *count; i += 1) {
    if (heap[i].response < heap[worst].response) {
      worst = i;
    }
  }
  if (response <= heap[worst].response) {
    return;
  }
  heap[worst].x = x;
  heap[worst].y = y;
  heap[worst].scale = scale;
  heap[worst].response = response;
}

static int32_t ad_align_up(int32_t value, int32_t step) {
  int32_t rem;
  if (step <= 1) {
    return value;
  }
  rem = value % step;
  if (rem == 0) {
    return value;
  }
  return value + (step - rem);
}

uint16_t ad_surf_detect(
  const AdFrame* frame,
  const AdConfig* cfg,
  AdSurfKeypoint* out_kps,
  uint16_t max_out,
  float* mean_response
) {
  int32_t* ii = 0;
  float* resp = 0;
  uint8_t* best_filter = 0;
  int32_t ii_w;
  int32_t w;
  int32_t h;
  int32_t step;
  uint8_t octaves;
  uint16_t count;
  double resp_sum;
  int32_t filter_sizes[6];
  uint8_t n_filters;
  uint8_t fi;
  int32_t grid_origin;

  if (mean_response != 0) {
    *mean_response = 0.0f;
  }
  if (frame == 0 || cfg == 0 || out_kps == 0 || max_out == 0) {
    return 0;
  }
  if (frame->data == 0 || frame->width < 16 || frame->height < 16) {
    return 0;
  }

  w = (int32_t)frame->width;
  h = (int32_t)frame->height;
  ii_w = w + 1;
  step = (int32_t)cfg->sample_step;
  if (step < 1) {
    step = 1;
  }
  octaves = cfg->surf_octaves;
  if (octaves < 1) {
    octaves = 1;
  }
  if (octaves > 2) {
    octaves = 2;
  }

  ii = (int32_t*)calloc((size_t)ii_w * (size_t)(h + 1), sizeof(int32_t));
  resp = (float*)calloc((size_t)w * (size_t)h, sizeof(float));
  best_filter = (uint8_t*)calloc((size_t)w * (size_t)h, sizeof(uint8_t));
  if (ii == 0 || resp == 0 || best_filter == 0) {
    free(ii);
    free(resp);
    free(best_filter);
    return 0;
  }

  ad_build_integral(frame, ii, ii_w);

  n_filters = 0;
  filter_sizes[n_filters++] = 9;
  filter_sizes[n_filters++] = 15;
  filter_sizes[n_filters++] = 21;
  if (octaves >= 2) {
    filter_sizes[n_filters++] = 27;
    filter_sizes[n_filters++] = 39;
  }

  grid_origin = ad_align_up(10, step);

  for (fi = 0; fi < n_filters; fi += 1) {
    int32_t filter = filter_sizes[fi];
    int32_t lobe = filter / 3;
    int32_t margin = ad_align_up(filter, step);
    int32_t y;
    int32_t x;

    if (margin * 2 >= w || margin * 2 >= h) {
      continue;
    }

    for (y = margin; y < h - margin; y += step) {
      for (x = margin; x < w - margin; x += step) {
        float r = ad_hessian_response(ii, ii_w, x, y, lobe);
        uint32_t idx = (uint32_t)y * (uint32_t)w + (uint32_t)x;
        if (r > resp[idx]) {
          resp[idx] = r;
          best_filter[idx] = (uint8_t)filter;
        }
      }
    }
  }

  count = 0;
  {
    int32_t y;
    int32_t x;
    float thresh = cfg->hessian_thresh;
    uint16_t ki;
    if (thresh < 0.0f) {
      thresh = 0.0f;
    }

    for (y = grid_origin; y < h - grid_origin; y += step) {
      for (x = grid_origin; x < w - grid_origin; x += step) {
        uint32_t idx = (uint32_t)y * (uint32_t)w + (uint32_t)x;
        float c = resp[idx];
        int32_t dy;
        int32_t dx;
        int is_max;
        float scale;

        if (c < thresh) {
          continue;
        }

        is_max = 1;
        for (dy = -step; dy <= step && is_max; dy += step) {
          for (dx = -step; dx <= step; dx += step) {
            float n;
            int32_t nx = x + dx;
            int32_t ny = y + dy;
            if (dx == 0 && dy == 0) {
              continue;
            }
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) {
              continue;
            }
            n = resp[(uint32_t)ny * (uint32_t)w + (uint32_t)nx];
            if (n > c) {
              is_max = 0;
              break;
            }
          }
        }
        if (!is_max) {
          continue;
        }

        scale = 1.2f * ((float)best_filter[idx] / 9.0f);
        if (scale < 1.0f) {
          scale = 1.0f;
        }
        ad_insert_topk(out_kps, &count, max_out, (float)x, (float)y, scale, c);
      }
    }

    resp_sum = 0.0;
    for (ki = 0; ki < count; ki += 1) {
      resp_sum += (double)out_kps[ki].response;
    }
    if (mean_response != 0 && count > 0) {
      *mean_response = (float)(resp_sum / (double)count);
    }
  }

  free(ii);
  free(resp);
  free(best_filter);
  return count;
}
