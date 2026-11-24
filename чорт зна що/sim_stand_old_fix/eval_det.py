import numpy as np, cv2, time
from common import *
svm = np.load('svm.npy'); det = Detector(svm[:-1], svm[-1])
rng = np.random.default_rng(7)
scenes = [make_scene(rng) for _ in range(40)]
conds = [(1.0,0,0),(0.3,0,0),(0.15,0,0),(1.0,10,0),(1.0,20,0),(1.0,0,9),(1.0,0,15),(0.3,10,9)]
for (e,s,L) in conds:
    allm=[]; ngt=0; ts=[]
    for img,boxes in scenes:
        d_img = degrade(img,e,s,L,rng)
        t=time.perf_counter(); d,sc = det.detect(d_img); ts.append(time.perf_counter()-t)
        allm += match(d,sc,boxes); ngt += len(boxes)
    print(f'e={e} sigma={s} L={L}  AP50={ap_from_matches(allm,ngt):.3f}  t_det={np.median(ts)*1000:.1f} ms')
