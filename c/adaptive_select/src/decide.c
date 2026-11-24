#include "adaptive.h"

#include <math.h>

AdDecision ad_decide(const AdAssess* assess, const AdConfig* cfg) {
  AdDecision best;

  best.route = AD_ROUTE_NONE;
  best.state = AD_STATE_OK;
  best.kind = AD_DAMAGE_NONE;
  best.health = 1.0f;
  best.damage = 0.0f;
  best.repair_cost = 0.0f;
  best.r = 0.0f;
  best.gamma = 1.0f;
  best.clahe_clip = 2.0f;

  if (assess == 0 || cfg == 0) {
    return best;
  }

  best.assess = *assess;
  best.state = assess->state;
  best.kind = assess->kind;
  best.r = assess->r;
  best.damage = assess->d_l;
  best.health = 1.0f - assess->d_l;

  if (assess->state == AD_STATE_OK) {
    return best;
  }

  if (assess->state == AD_STATE_BAD) {
    best.route = AD_ROUTE_NONE;
    best.repair_cost = 1.0e9f;
    return best;
  }

  if (assess->kind == AD_DAMAGE_MIXED) {
    best.route = AD_ROUTE_CLAHE;
    best.clahe_clip = cfg->clahe_clip_min + cfg->clahe_clip_span * assess->r;
    best.repair_cost = cfg->cost_base_clahe + cfg->cost_per_r_clahe * assess->r;
    return best;
  }

  if (assess->kind == AD_DAMAGE_UNDER) {
    best.route = AD_ROUTE_GAMMA_LIGHT;
    best.gamma = 1.0f - 0.5f * assess->r;
    best.repair_cost = cfg->cost_base_point + cfg->cost_per_r_point * assess->r;
    return best;
  }

  if (assess->kind == AD_DAMAGE_OVER) {
    if (assess->ps >= 0.12f && assess->d_u >= 0.18f) {
      best.route = AD_ROUTE_CLAHE;
      best.kind = AD_DAMAGE_MIXED;
      best.clahe_clip = cfg->clahe_clip_min + cfg->clahe_clip_span * fmaxf(assess->r, 0.45f);
      best.repair_cost = cfg->cost_base_clahe + cfg->cost_per_r_clahe * assess->r;
      return best;
    }
    best.route = AD_ROUTE_GAMMA_DARK;
    best.gamma = 1.0f + assess->r;
    best.repair_cost = cfg->cost_base_point + cfg->cost_per_r_point * assess->r;
    return best;
  }

  best.route = AD_ROUTE_STRETCH;
  best.repair_cost = cfg->cost_base_point + cfg->cost_per_r_point * assess->r;
  return best;
}
