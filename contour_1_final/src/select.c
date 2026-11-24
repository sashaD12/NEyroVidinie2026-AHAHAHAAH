#include "adaptive.h"

AdRoute ad_select_route(const float* v) {
  uint32_t node = 0;
  uint32_t steps = 0;
  if (v == 0 || ad_tree_size == 0) {
    return AD_ROUTE_NONE;
  }
  while (ad_tree_nodes[node].left >= 0 && steps < ad_tree_size) {
    const AdTreeNode* t = &ad_tree_nodes[node];
    if ((double)v[t->feature] <= t->threshold) {
      node = (uint32_t)t->left;
    } else {
      node = (uint32_t)t->right;
    }
    if (node >= ad_tree_size) {
      return AD_ROUTE_NONE;
    }
    steps += 1;
  }
  if (ad_tree_nodes[node].route >= AD_ROUTE_COUNT) {
    return AD_ROUTE_NONE;
  }
  return (AdRoute)ad_tree_nodes[node].route;
}
