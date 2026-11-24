#include "adaptive.h"

const char* ad_route_name(AdRoute route) {
  if (route == AD_ROUTE_NONE) {
    return "NONE";
  }
  if (route == AD_ROUTE_GAMMA) {
    return "GAMMA";
  }
  if (route == AD_ROUTE_CLAHE) {
    return "CLAHE";
  }
  if (route == AD_ROUTE_STRETCH) {
    return "STRETCH";
  }
  if (route == AD_ROUTE_MEDIAN) {
    return "MEDIAN";
  }
  if (route == AD_ROUTE_DEBLUR) {
    return "DEBLUR";
  }
  return "UNKNOWN";
}

const char* ad_kind_name(AdDamageKind kind) {
  if (kind == AD_DAMAGE_UNDER) {
    return "under";
  }
  if (kind == AD_DAMAGE_OVER) {
    return "over";
  }
  if (kind == AD_DAMAGE_CONTRAST) {
    return "contrast";
  }
  if (kind == AD_DAMAGE_MIXED) {
    return "mixed";
  }
  if (kind == AD_DAMAGE_NOISE) {
    return "noise";
  }
  if (kind == AD_DAMAGE_BLUR) {
    return "blur";
  }
  return "none";
}

const char* ad_state_name(AdState state) {
  if (state == AD_STATE_REPAIR) {
    return "repair";
  }
  if (state == AD_STATE_BAD) {
    return "bad";
  }
  return "ok";
}
