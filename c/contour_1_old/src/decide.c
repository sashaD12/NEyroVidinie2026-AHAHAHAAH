#include "adaptive.h"

#include <math.h>

static void ad_cand_clear(AdCandidateList* out) {
  uint8_t i;
  if (out == 0) {
    return;
  }
  out->count = 0;
  for (i = 0; i < AD_MAX_CANDIDATES; i += 1) {
    out->items[i].route = AD_ROUTE_NONE;
    out->items[i].repair_cost = 0.0f;
    out->items[i].gamma = 1.0f;
    out->items[i].clahe_clip = 2.0f;
    out->items[i].sharpen_amount = 0.0f;
  }
}

static void ad_cand_add(
  AdCandidateList* out,
  AdRoute route,
  float cost,
  float gamma,
  float clahe_clip,
  float sharpen_amount
) {
  AdRouteCandidate* c;
  if (out == 0 || out->count >= AD_MAX_CANDIDATES) {
    return;
  }
  c = &out->items[out->count];
  c->route = route;
  c->repair_cost = cost;
  c->gamma = gamma;
  c->clahe_clip = clahe_clip;
  c->sharpen_amount = sharpen_amount;
  out->count = (uint8_t)(out->count + 1);
}

void ad_decide_candidates(const AdAssess* assess, const AdConfig* cfg, AdCandidateList* out) {
  float r;
  float cost_point;
  float cost_spatial;
  float cost_clahe;
  float gamma_light;
  float gamma_dark;
  float clahe_clip;

  ad_cand_clear(out);
  if (assess == 0 || cfg == 0 || out == 0) {
    return;
  }

  r = assess->r;
  cost_point = cfg->cost_base_point + cfg->cost_per_r_point * r;
  cost_spatial = cfg->cost_base_spatial + cfg->cost_per_r_spatial * r;
  cost_clahe = cfg->cost_base_clahe + cfg->cost_per_r_clahe * r;
  gamma_light = 1.0f - 0.5f * r;
  gamma_dark = 1.0f + r;
  clahe_clip = cfg->clahe_clip_min + cfg->clahe_clip_span * r;

  ad_cand_add(out, AD_ROUTE_NONE, 0.0f, 1.0f, 2.0f, 0.0f);

  if (assess->state == AD_STATE_OK) {
    return;
  }

  if (assess->state == AD_STATE_BAD) {
    out->items[0].repair_cost = 1.0e9f;
    return;
  }

  if (assess->kind == AD_DAMAGE_BLUR) {
    ad_cand_add(out, AD_ROUTE_SHARPEN, cost_spatial, 1.0f, 2.0f, 0.4f + 0.8f * r);
    return;
  }

  if (assess->kind == AD_DAMAGE_NOISE) {
    ad_cand_add(out, AD_ROUTE_DENOISE, cost_spatial, 1.0f, 2.0f, 0.0f);
    return;
  }

  if (assess->kind == AD_DAMAGE_UNDER) {
    ad_cand_add(out, AD_ROUTE_GAMMA_LIGHT, cost_point, gamma_light, 2.0f, 0.0f);
    ad_cand_add(out, AD_ROUTE_CLAHE, cost_clahe, 1.0f, clahe_clip, 0.0f);
    return;
  }

  if (assess->kind == AD_DAMAGE_OVER) {
    ad_cand_add(out, AD_ROUTE_GAMMA_DARK, cost_point, gamma_dark, 2.0f, 0.0f);
    ad_cand_add(out, AD_ROUTE_CLAHE, cost_clahe, 1.0f, fmaxf(clahe_clip, 0.45f * cfg->clahe_clip_span + cfg->clahe_clip_min), 0.0f);
    return;
  }

  if (assess->kind == AD_DAMAGE_MIXED) {
    ad_cand_add(out, AD_ROUTE_CLAHE, cost_clahe, 1.0f, clahe_clip, 0.0f);
    return;
  }

  if (assess->kind == AD_DAMAGE_CONTRAST) {
    ad_cand_add(out, AD_ROUTE_STRETCH, cost_point, 1.0f, 2.0f, 0.0f);
    ad_cand_add(out, AD_ROUTE_CLAHE, cost_clahe, 1.0f, clahe_clip, 0.0f);
    return;
  }
}

AdDecision ad_pick_cheapest(
  const AdAssess* assess,
  const AdConfig* cfg,
  const AdCandidateList* candidates
) {
  AdDecision best;
  uint8_t i;
  uint8_t best_i;
  float damage;

  best.route = AD_ROUTE_NONE;
  best.state = AD_STATE_OK;
  best.kind = AD_DAMAGE_NONE;
  best.health = 1.0f;
  best.damage = 0.0f;
  best.repair_cost = 0.0f;
  best.r = 0.0f;
  best.gamma = 1.0f;
  best.clahe_clip = 2.0f;
  best.sharpen_amount = 0.0f;
  ad_cand_clear(&best.candidates);

  if (assess == 0 || cfg == 0) {
    return best;
  }

  damage = fmaxf(assess->d_l, assess->d_s);
  best.assess = *assess;
  best.state = assess->state;
  best.kind = assess->kind;
  best.r = assess->r;
  best.damage = damage;
  best.health = 1.0f - damage;
  if (candidates != 0) {
    best.candidates = *candidates;
  }

  if (assess->state == AD_STATE_OK) {
    return best;
  }

  if (assess->state == AD_STATE_BAD || candidates == 0 || candidates->count == 0) {
    best.route = AD_ROUTE_NONE;
    best.repair_cost = 1.0e9f;
    return best;
  }

  best_i = 0;
  for (i = 0; i < candidates->count; i += 1) {
    if (candidates->items[i].route == AD_ROUTE_NONE) {
      continue;
    }
    if (best_i == 0 || candidates->items[best_i].route == AD_ROUTE_NONE) {
      best_i = i;
      continue;
    }
    if (candidates->items[i].repair_cost < candidates->items[best_i].repair_cost) {
      best_i = i;
    }
  }

  if (candidates->items[best_i].route == AD_ROUTE_NONE) {
    best.route = AD_ROUTE_NONE;
    best.repair_cost = candidates->items[best_i].repair_cost;
    return best;
  }

  best.route = candidates->items[best_i].route;
  best.repair_cost = candidates->items[best_i].repair_cost;
  best.gamma = candidates->items[best_i].gamma;
  best.clahe_clip = candidates->items[best_i].clahe_clip;
  best.sharpen_amount = candidates->items[best_i].sharpen_amount;
  return best;
}

AdDecision ad_decide(const AdAssess* assess, const AdConfig* cfg) {
  AdCandidateList list;
  ad_decide_candidates(assess, cfg, &list);
  return ad_pick_cheapest(assess, cfg, &list);
}
