"""D435i + ViTPose 2D skeleton — standalone version."""
import os, sys, time, cv2, numpy as np, torch, pyrealsense2 as rs
from pathlib import Path
os.environ["PYOPENGL_PLATFORM"] = "wgl"; np.bool = bool

# Add parent dir to path so vitpose_model.py is findable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vitpose_model import ViTPoseModel

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--max_frames", type=int, default=None)
ap.add_argument("--headless", action="store_true")
args, _ = ap.parse_known_args()

print("Loading ViTPose ...", end=" ", flush=True)
t1 = time.time()
cpm = ViTPoseModel("cuda")
print(f"done ({time.time()-t1:.1f}s)")

print("D435i ...", end=" ", flush=True)
pipe = rs.pipeline(); cfg = rs.config()
cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
prof = pipe.start(cfg)
print(f"OK ({prof.get_device().get_info(rs.camera_info.serial_number)})")

BODY_EDGES = [(0,1),(0,2),(1,3),(2,4),(0,5),(5,7),(7,9),(0,6),(6,8),(8,10),(5,11),(11,13),(13,15),(6,12),(12,14),(14,16)]
HAND_EDGES = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),(18,19),(19,20)]
fc=0; ft=time.time(); fps=0; vit_skip=0; frame_count=0; max_frames=args.max_frames
last_body=None; last_body_v=None; last_hands=[]
print("Running (q to quit)..." if not args.headless else "Headless...")

while True:
    ts=time.time()
    frames=pipe.wait_for_frames(timeout_ms=5000)
    f=np.asanyarray(frames.get_color_frame().get_data())
    canvas=f.copy(); h,w=f.shape[:2]
    if vit_skip<=0:
        vit_skip=4
        vitposes=cpm.predict_pose(f,[np.array([[0,0,w,h,0.9]])])
        last_hands=[]
        for vp in vitposes:
            kps=vp["keypoints"]
            body=kps[:17]; bv=body[:,2]>0.5
            last_body=body; last_body_v=bv
            for hk,clr in [(kps[-42:-21],(0,200,255)),(kps[-21:],(255,100,0))]:
                last_hands.append((hk,clr,hk[:,2]>0.5))
    else:
        vit_skip-=1
    if last_body is not None:
        for e in BODY_EDGES:
            if last_body_v[e[0]] and last_body_v[e[1]]:
                cv2.line(canvas,(int(last_body[e[0],0]),int(last_body[e[0],1])),
                         (int(last_body[e[1],0]),int(last_body[e[1],1])),(0,255,255),2)
        for i,kp in enumerate(last_body):
            if last_body_v[i]: cv2.circle(canvas,(int(kp[0]),int(kp[1])),4,(0,255,0),-1)
    for hk,clr,v in last_hands:
        if sum(v)>=8:
            for e in HAND_EDGES:
                if v[e[0]] and v[e[1]]:
                    cv2.line(canvas,(int(hk[e[0],0]),int(hk[e[0],1])),
                             (int(hk[e[1],0]),int(hk[e[1],1])),clr,2)
            for kp in hk[v]: cv2.circle(canvas,(int(kp[0]),int(kp[1])),5,clr,-1)
    frame_count+=1; fc+=1
    if time.time()-ft>=1: fps,fc,ft=fc,0,time.time()
    if max_frames and frame_count>=max_frames: print(f"Done: {frame_count}"); break
    if not args.headless:
        cv2.putText(canvas,f"FPS:{fps}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,200,0),2)
        cv2.imshow("D435i+ViTPose",canvas)
        if cv2.waitKey(1)&0xFF in (ord("q"),27): break
pipe.stop(); cv2.destroyAllWindows()
