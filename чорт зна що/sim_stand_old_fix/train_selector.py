import os
import sys

import numpy as np
from sklearn.tree import DecisionTreeClassifier

import c1lib
from common import BLUR, EXPOSURE, NOISE, PIPELINE_ROUTES, degrade, make_scene

EPS = 0.05
SEED = 20261113
N_PER = 40
OUT_C = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "c", "contour_1_old_fix", "src", "selector_tree.c"))
COST = {
    0: 0.0,
    1: 1.0,
    2: 1.1,
    3: 1.4,
    4: 2.0,
    5: 1.3,
    6: 1.5,
}


def damage(q):
    return float(np.max(q))


def reference_route(img):
    q0, _d = c1lib.assess(img)
    d0 = damage(q0)
    scores = []
    for rid in range(c1lib.ROUTE_COUNT):
        out = c1lib.route(img, rid, q0)
        q1, _ = c1lib.assess(out)
        scores.append((damage(q1), COST.get(rid, 10.0 + rid), rid))
    best = min(s[0] for s in scores)
    ok = [s for s in scores if s[0] <= best + EPS]
    if d0 < 0.25:
        return q0, 0
    repaired = [s for s in ok if s[2] != 0]
    if d0 >= 0.35 and repaired:
        ok = repaired
    ok.sort(key=lambda s: (s[1], s[2]))
    return q0, ok[0][2]


def collect():
    rng = np.random.default_rng(SEED)
    xs = []
    ys = []
    for e in EXPOSURE:
        for s in NOISE:
            for L in BLUR:
                for _ in range(N_PER):
                    img, _boxes = make_scene(rng)
                    d = degrade(img, e, s, L, rng)
                    q, y = reference_route(d)
                    xs.append(q)
                    ys.append(y)
    return np.asarray(xs, np.float32), np.asarray(ys, np.int32)


def export_tree(clf, path):
    tree = clf.tree_
    classes = [int(c) for c in clf.classes_]
    lines = [
        '#include "adaptive.h"',
        "",
        "const AdTreeNode ad_tree_nodes[] = {",
    ]
    for i in range(tree.node_count):
        left = int(tree.children_left[i])
        right = int(tree.children_right[i])
        if left < 0:
            route = classes[int(np.argmax(tree.value[i][0]))]
            lines.append(f"  {{0.0, -1, -1, -1, {route}}},")
        else:
            feat = int(tree.feature[i])
            thr = float(tree.threshold[i])
            lines.append(f"  {{{thr:.9g}, {feat}, {left}, {right}, 0}},")
    lines.append("};")
    lines.append("")
    lines.append(f"const uint32_t ad_tree_size = {tree.node_count};")
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main():
    print("routes", PIPELINE_ROUTES, "count", c1lib.ROUTE_COUNT)
    x, y = collect()
    print("samples", len(y), "unique routes", sorted(set(int(v) for v in y)))
    clf = DecisionTreeClassifier(max_depth=6, min_samples_leaf=8, random_state=0)
    clf.fit(x, y)
    acc = float((clf.predict(x) == y).mean())
    print(f"train accuracy={acc:.3f} nodes={clf.tree_.node_count}")
    export_tree(clf, OUT_C)
    print("wrote", OUT_C)
    counts = {int(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))}
    print("label counts", counts)


if __name__ == "__main__":
    main()
