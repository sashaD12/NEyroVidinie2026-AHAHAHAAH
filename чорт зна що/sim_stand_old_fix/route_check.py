import numpy as np, cv2, time
from common import *
svm = np.load('svm.npy'); det = Detector(svm[:-1], svm[-1])
rng = np.random.default_rng(11)
scenes = [make_scene(rng) for _ in range(20)]
conds = [(1.0,0,0),(0.5,0,0),(0.3,0,0),(0.15,0,0),(1.0,5,0),(1.0,10,0),(1.0,0,5),(1.0,0,9),(0.5,5,5)]
print('cond'.ljust(16)+''.join(n[:9].rjust(10) for n in ROUTE_NAMES))
for (e,s,L) in conds:
    degs=[degrade(img,e,s,L,rng) for img,_ in scenes]
    row=[]
    for rn,f in ROUTES.items():
        allm=[];ngt=0
        for d,(img,boxes) in zip(degs,scenes):
            dd,sc=det.detect(f(d)); allm+=match(dd,sc,boxes); ngt+=len(boxes)
        row.append(ap_from_matches(allm,ngt))
    print(f'e={e} s={s} L={L}'.ljust(16)+''.join(f'{v:10.3f}' for v in row), flush=True)
