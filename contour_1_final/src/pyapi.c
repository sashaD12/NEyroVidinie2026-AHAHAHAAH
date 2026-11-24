#include "adaptive.h"

#ifdef _WIN32
#define AD_API __declspec(dllexport)
#else
#define AD_API __attribute__((visibility("default")))
#endif

#define AD_PY_DIAG 14

static AdConfig ad_py_cfg;
static int ad_py_ready = 0;

static const AdConfig* ad_py_config(void) {
  if (!ad_py_ready) {
    ad_config_default(&ad_py_cfg);
    ad_py_ready = 1;
  }
  return &ad_py_cfg;
}

static int ad_py_frame(uint8_t* data, int width, int height, int stride, AdFrame* frame) {
  if (data == 0 || width <= 0 || height <= 0 || width > 65535 || height > 65535 || stride < width || stride > 65535) {
    return 0;
  }
  frame->data = data;
  frame->width = (uint16_t)width;
  frame->height = (uint16_t)height;
  frame->stride = (uint16_t)stride;
  return 1;
}

AD_API int ad_py_diag_size(void) {
  return AD_PY_DIAG;
}

AD_API int ad_py_route_count(void) {
  return (int)AD_ROUTE_COUNT;
}

AD_API int ad_py_assess(const uint8_t* data, int width, int height, int stride, float* vec, float* diag) {
  AdFrame frame;
  AdAssess assess;
  int i;
  if (vec == 0 || !ad_py_frame((uint8_t*)data, width, height, stride, &frame)) {
    return 0;
  }
  ad_assess_frame(&frame, ad_py_config(), &assess);
  for (i = 0; i < AD_VEC_DIM; i += 1) {
    vec[i] = assess.v[i];
  }
  if (diag != 0) {
    diag[0] = assess.s_L;
    diag[1] = assess.n_flat;
    diag[2] = (float)assess.flat_count;
    diag[3] = assess.aniso;
    diag[4] = assess.e_max;
    diag[5] = assess.d_motion;
    diag[6] = (float)assess.log_kind;
    diag[7] = (float)assess.log_state;
    diag[8] = assess.log_r;
    diag[9] = assess.mu;
    diag[10] = assess.sigma;
    diag[11] = (float)assess.sample_count;
    diag[12] = assess.s_L_raw;
    diag[13] = assess.noise_sigma;
  }
  return 1;
}

AD_API int ad_py_route(uint8_t* data, int width, int height, int stride, int route, const float* vec) {
  AdFrame frame;
  if (vec == 0 || route < 0 || route >= (int)AD_ROUTE_COUNT || !ad_py_frame(data, width, height, stride, &frame)) {
    return 0;
  }
  ad_apply_route(&frame, (AdRoute)route, vec, ad_py_config());
  return 1;
}

AD_API int ad_py_select(const float* vec) {
  return (int)ad_select_route(vec);
}

AD_API int ad_py_config_values(float* out, int n) {
  const AdConfig* cfg = ad_py_config();
  float values[3];
  int i;
  values[0] = cfg->s_L0;
  values[1] = cfg->n0;
  values[2] = cfg->flat_frac;
  if (out == 0) {
    return 0;
  }
  for (i = 0; i < n && i < 3; i += 1) {
    out[i] = values[i];
  }
  return 3;
}
