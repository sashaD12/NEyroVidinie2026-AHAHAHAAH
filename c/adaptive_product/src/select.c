#include "adaptive.h"

void ad_budget_reset(AdBudget* budget) {
  uint8_t i;
  if (budget == 0) {
    return;
  }
  budget->count = 0;
  for (i = 0; i < AD_BUDGET; i += 1) {
    budget->slots[i].frame_id = 0;
    budget->slots[i].repair_cost = 0.0f;
    budget->slots[i].damage = 0.0f;
    budget->slots[i].route = AD_ROUTE_NONE;
    budget->slots[i].state = AD_STATE_OK;
    budget->slots[i].used = 0;
  }
}

int ad_budget_better(const AdDecision* a, const AdDecision* b) {
  if (a == 0) {
    return 0;
  }
  if (b == 0) {
    return 1;
  }
  if (a->state == AD_STATE_BAD) {
    return 0;
  }
  if (b->state == AD_STATE_BAD) {
    return 1;
  }
  if (a->state == AD_STATE_OK && b->state != AD_STATE_OK) {
    return 1;
  }
  if (b->state == AD_STATE_OK && a->state != AD_STATE_OK) {
    return 0;
  }
  if (a->state == AD_STATE_OK && b->state == AD_STATE_OK) {
    return a->damage < b->damage;
  }
  return a->repair_cost < b->repair_cost;
}

void ad_budget_offer(AdBudget* budget, uint32_t frame_id, const AdDecision* decision) {
  uint8_t i;
  uint8_t worst = 0;
  AdCandidate probe;

  if (budget == 0 || decision == 0) {
    return;
  }
  if (decision->state == AD_STATE_BAD) {
    return;
  }

  probe.frame_id = frame_id;
  probe.repair_cost = decision->repair_cost;
  probe.damage = decision->damage;
  probe.route = decision->route;
  probe.state = decision->state;
  probe.used = 1;

  if (budget->count < AD_BUDGET) {
    budget->slots[budget->count] = probe;
    budget->count = (uint8_t)(budget->count + 1);
    return;
  }

  for (i = 1; i < AD_BUDGET; i += 1) {
    AdDecision cur;
    AdDecision wrs;
    cur.state = budget->slots[i].state;
    cur.damage = budget->slots[i].damage;
    cur.repair_cost = budget->slots[i].repair_cost;
    wrs.state = budget->slots[worst].state;
    wrs.damage = budget->slots[worst].damage;
    wrs.repair_cost = budget->slots[worst].repair_cost;
    if (ad_budget_better(&wrs, &cur)) {
      worst = i;
    }
  }

  {
    AdDecision worst_dec;
    worst_dec.state = budget->slots[worst].state;
    worst_dec.damage = budget->slots[worst].damage;
    worst_dec.repair_cost = budget->slots[worst].repair_cost;
    if (!ad_budget_better(decision, &worst_dec)) {
      return;
    }
  }

  budget->slots[worst] = probe;
}

int ad_budget_contains(const AdBudget* budget, uint32_t frame_id) {
  uint8_t i;
  if (budget == 0) {
    return 0;
  }
  for (i = 0; i < budget->count; i += 1) {
    if (budget->slots[i].used != 0 && budget->slots[i].frame_id == frame_id) {
      return 1;
    }
  }
  return 0;
}
