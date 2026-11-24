#include "adaptive.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failed = 0;

static void expect_true(int cond, const char* name) {
  if (!cond) {
    fprintf(stderr, "FAIL: %s\n", name);
    g_failed += 1;
  } else {
    printf("PASS: %s\n", name);
  }
}

static void fill_gray(AdFrame* frame, uint8_t value) {
  uint32_t n = (uint32_t)frame->height * (uint32_t)frame->stride;
  uint32_t i;
  for (i = 0; i < n; i += 1) {
    frame->data[i] = value;
  }
}

static void fill_ramp(AdFrame* frame) {
  uint32_t y;
  uint32_t x;
  for (y = 0; y < frame->height; y += 1) {
    for (x = 0; x < frame->width; x += 1) {
      frame->data[y * frame->stride + x] = (uint8_t)((x * 255) / (frame->width > 1 ? frame->width - 1 : 1));
    }
  }
}

static void fill_split(AdFrame* frame) {
  uint32_t y;
  uint32_t x;
  for (y = 0; y < frame->height; y += 1) {
    for (x = 0; x < frame->width; x += 1) {
      frame->data[y * frame->stride + x] = (x < frame->width / 2) ? 8 : 250;
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

static void test_assess_and_decide(void) {
  AdConfig cfg;
  AdAssess assess;
  AdDecision decision;
  uint8_t* owned = 0;
  AdFrame frame = make_frame(320, 240, &owned);

  ad_config_default(&cfg);

  fill_ramp(&frame);
  ad_assess_frame(&frame, &cfg, &assess);
  decision = ad_decide(&assess, &cfg);
  expect_true(assess.state == AD_STATE_OK, "normal ramp is OK");
  expect_true(decision.route == AD_ROUTE_NONE, "normal ramp route NONE");

  fill_gray(&frame, 20);
  ad_assess_frame(&frame, &cfg, &assess);
  decision = ad_decide(&assess, &cfg);
  expect_true(assess.d_u > assess.d_o, "dark frame d_u dominant");
  expect_true(assess.state == AD_STATE_REPAIR || assess.state == AD_STATE_BAD, "dark needs attention");
  if (assess.state == AD_STATE_REPAIR) {
    expect_true(decision.route == AD_ROUTE_GAMMA_LIGHT, "dark route GAMMA_LIGHT");
  }

  fill_gray(&frame, 240);
  ad_assess_frame(&frame, &cfg, &assess);
  decision = ad_decide(&assess, &cfg);
  expect_true(assess.d_o > assess.d_u, "bright frame d_o dominant");
  if (assess.state == AD_STATE_REPAIR) {
    expect_true(decision.route == AD_ROUTE_GAMMA_DARK || decision.route == AD_ROUTE_CLAHE,
                "bright route deover or clahe");
  }

  {
    uint32_t n;
    uint32_t i;
    uint32_t hi_before = 0;
    uint32_t hi_after = 0;
    fill_gray(&frame, 250);
    for (i = 0; i < 32; i += 1) {
      frame.data[i] = 40;
    }
    n = (uint32_t)frame.width * (uint32_t)frame.height;
    for (i = 0; i < n; i += 1) {
      if (frame.data[i] >= 245) {
        hi_before += 1;
      }
    }
    ad_assess_frame(&frame, &cfg, &assess);
    assess.state = AD_STATE_REPAIR;
    assess.kind = AD_DAMAGE_OVER;
    assess.r = 0.55f;
    assess.ps = 0.0f;
    decision = ad_decide(&assess, &cfg);
    ad_apply_route(&frame, &decision, &cfg);
    for (i = 0; i < n; i += 1) {
      if (frame.data[i] >= 245) {
        hi_after += 1;
      }
    }
    expect_true(decision.route == AD_ROUTE_GAMMA_DARK, "forced over uses deover route");
    expect_true(hi_after < hi_before, "deover reduces clipped highlights");
  }

  fill_gray(&frame, 100);
  ad_assess_frame(&frame, &cfg, &assess);
  expect_true(assess.d_c > 0.2f, "flat frame low contrast");

  fill_split(&frame);
  ad_assess_frame(&frame, &cfg, &assess);
  expect_true(assess.kind == AD_DAMAGE_MIXED || (assess.d_u >= cfg.tau_l && assess.d_o >= cfg.tau_l),
              "split frame mixed light");

  free(owned);
}

static void test_budget(void) {
  AdBudget budget;
  AdDecision cheap;
  AdDecision expensive;
  AdDecision ok;

  memset(&cheap, 0, sizeof(cheap));
  memset(&expensive, 0, sizeof(expensive));
  memset(&ok, 0, sizeof(ok));

  cheap.state = AD_STATE_REPAIR;
  cheap.route = AD_ROUTE_GAMMA_DARK;
  cheap.repair_cost = 0.2f;
  cheap.damage = 0.4f;

  expensive.state = AD_STATE_REPAIR;
  expensive.route = AD_ROUTE_CLAHE;
  expensive.repair_cost = 2.5f;
  expensive.damage = 0.7f;

  ok.state = AD_STATE_OK;
  ok.route = AD_ROUTE_NONE;
  ok.repair_cost = 0.0f;
  ok.damage = 0.1f;

  ad_budget_reset(&budget);
  ad_budget_offer(&budget, 1, &expensive);
  ad_budget_offer(&budget, 2, &cheap);
  ad_budget_offer(&budget, 3, &ok);
  expect_true(budget.count == 3, "budget accepted three frames");
  expect_true(ad_budget_contains(&budget, 2), "budget keeps cheap id");
  expect_true(ad_budget_better(&ok, &cheap), "OK better than repair");
  expect_true(ad_budget_better(&cheap, &expensive), "cheap better than expensive");
}

static void test_routes_change_pixels(void) {
  AdConfig cfg;
  AdAssess assess;
  AdDecision decision;
  uint8_t* owned = 0;
  AdFrame frame = make_frame(64, 48, &owned);
  uint8_t before;
  uint32_t sum_before = 0;
  uint32_t sum_after = 0;
  uint32_t i;
  uint32_t n;

  ad_config_default(&cfg);
  fill_gray(&frame, 30);
  n = (uint32_t)frame.width * (uint32_t)frame.height;
  for (i = 0; i < n; i += 1) {
    sum_before += frame.data[i];
  }
  before = frame.data[0];
  ad_assess_frame(&frame, &cfg, &assess);
  assess.state = AD_STATE_REPAIR;
  assess.kind = AD_DAMAGE_UNDER;
  assess.r = 0.6f;
  decision = ad_decide(&assess, &cfg);
  ad_apply_route(&frame, &decision, &cfg);
  for (i = 0; i < n; i += 1) {
    sum_after += frame.data[i];
  }
  expect_true(decision.route == AD_ROUTE_GAMMA_LIGHT, "forced under uses gamma light");
  expect_true(sum_after > sum_before, "gamma light brightens dark frame");
  expect_true(frame.data[0] != before || sum_after != sum_before, "pixels changed");

  fill_ramp(&frame);
  ad_assess_frame(&frame, &cfg, &assess);
  assess.state = AD_STATE_REPAIR;
  assess.kind = AD_DAMAGE_CONTRAST;
  assess.r = 0.5f;
  decision = ad_decide(&assess, &cfg);
  ad_apply_route(&frame, &decision, &cfg);
  expect_true(decision.route == AD_ROUTE_STRETCH, "contrast uses stretch");

  free(owned);
}

static void test_pipeline_photo(void) {
  AdConfig cfg;
  AdProcessResult result;
  uint8_t* owned = 0;
  AdFrame frame = make_frame(128, 96, &owned);
  uint32_t sum_before = 0;
  uint32_t sum_after = 0;
  uint32_t i;
  uint32_t n;

  ad_config_default(&cfg);
  fill_gray(&frame, 25);
  n = (uint32_t)frame.width * (uint32_t)frame.height;
  for (i = 0; i < n; i += 1) {
    sum_before += frame.data[i];
  }
  result = ad_process_frame(&frame, &cfg);
  for (i = 0; i < n; i += 1) {
    sum_after += frame.data[i];
  }
  expect_true(result.applied == 1, "pipeline applies repair on dark photo");
  expect_true(sum_after > sum_before, "pipeline brightens dark photo");

  free(owned);
}

int main(void) {
  test_assess_and_decide();
  test_budget();
  test_routes_change_pixels();
  test_pipeline_photo();
  if (g_failed != 0) {
    fprintf(stderr, "\n%d test(s) failed\n", g_failed);
    return 1;
  }
  printf("\nAll tests passed\n");
  return 0;
}
