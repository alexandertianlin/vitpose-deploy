"""ViTPose + D435i: wait for hand, record 10s, latency report."""
import os,sys,time,cv2,numpy as np,torch,pyrealsense2 as rs,json
from pathlib import Path
os.environ["PYOPENGL_PLATFORM"]="wgl";np.bool=bool
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from vitpose_model import ViTPoseModel

OUT=Path(__file__).resolve().parent.parent/"outputs";OUT.mkdir(parents=True,exist_ok=True)
print("Loading ViTPose...",end=" ",flush=True)
t1=time.time();cpm=ViTPoseModel("cuda");print(f"done ({time.time()-t1:.1f}s)")
print("D435i...",end=" ",flush=True)
pipe=rs.pipeline();cfg=rs.config()
cfg.enable_stream(rs.stream.color,640,480,rs.format.bgr8,30)
prof=pipe.start(cfg);print(f"OK ({prof.get_device().get_info(rs.camera_info.serial_number)})")

REC_SEC=10;fc=0;ft=time.time();fps=0;vit_skip=0;fcnt=0;rec=False;rs_=None
BODY_EDGES=[(0,1),(0,2),(1,3),(2,4),(0,5),(5,7),(7,9),(0,6),(6,8),(8,10),(5,11),(11,13),(13,15),(6,12),(12,14),(14,16)]
HAND_EDGES=[(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),(18,19),(19,20)]
tms={"cap_ms":[],"vit_ms":[],"total_ms":[],"hand_cnt":[]}
lb=None;lbv=None;lhs=[]
print(f"\n等待手部...伸入手后录制{REC_SEC}秒")

while True:
    ts=time.time()
    f=np.asanyarray(pipe.wait_for_frames(timeout_ms=5000).get_color_frame().get_data())
    cv2.putText((canvas:=f.copy()),"",(0,0),cv2.FONT_HERSHEY_SIMPLEX,0,(0,0,0),0)
    h,w=f.shape[:2]
    if vit_skip<=0:
        vit_skip=4;tv=time.time()
        vps=cpm.predict_pose(f,[np.array([[0,0,w,h,0.9]])]);vm=(time.time()-tv)*1000;lhs=[]
        for vp in vps:
            kps=vp["keypoints"];body=kps[:17];lb=body;lbv=body[:,2]>0.5
            for hk,clr in [(kps[-42:-21],(0,200,255)),(kps[-21:],(255,100,0))]:lhs.append((hk,clr,hk[:,2]>0.5))
        hcnt=sum(1 for _,_,v in lhs if sum(v)>=8)
        if hcnt>0 and not rec:rec=True;rs_=time.time();print(f"\n>>> 检测到手! 录制{REC_SEC}秒...")
        if rec:tms["cap_ms"].append((time.time()-ts)*1000);tms["vit_ms"].append(vm);tms["total_ms"].append((time.time()-ts)*1000);tms["hand_cnt"].append(hcnt)
    else:vit_skip-=1
    if lb is not None:
        for e in BODY_EDGES:
            if lbv[e[0]] and lbv[e[1]]:cv2.line(canvas,(int(lb[e[0],0]),int(lb[e[0],1])),(int(lb[e[1],0]),int(lb[e[1],1])),(0,255,255),2)
        for i,kp in enumerate(lb):
            if lbv[i]:cv2.circle(canvas,(int(kp[0]),int(kp[1])),4,(0,255,0),-1)
    for hk,clr,v in lhs:
        if sum(v)>=8:
            for e in HAND_EDGES:
                if v[e[0]] and v[e[1]]:cv2.line(canvas,(int(hk[e[0],0]),int(hk[e[0],1])),(int(hk[e[1],0]),int(hk[e[1],1])),clr,2)
            for kp in hk[v]:cv2.circle(canvas,(int(kp[0]),int(kp[1])),5,clr,-1)
    fcnt+=1;fc+=1
    if time.time()-ft>=1:fps,fc,ft=fc,0,time.time()
    cv2.putText(canvas,f"FPS:{fps}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,200,0),2)
    if rec:
        el=time.time()-rs_
        cv2.putText(canvas,f"REC {el:.1f}s/{REC_SEC}s",(10,60),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
        if el>=REC_SEC:print(f"\n>>> {REC_SEC}秒到");break
    else:cv2.putText(canvas,"等待手部...",(10,60),cv2.FONT_HERSHEY_SIMPLEX,.6,(200,200,0),2)
    cv2.imshow("D435i+ViTPose",canvas)
    if cv2.waitKey(1)&0xFF in (ord("q"),27):break
pipe.stop();cv2.destroyAllWindows()
print("\n"+"="*60);print("延迟报告");print("="*60)
def st(a,l):
    if not a:return;x=np.array(a);print(f"  {l}: mean={x.mean():.0f}ms p50={np.percentile(x,50):.0f}ms p95={np.percentile(x,95):.0f}ms")
st(tms["cap_ms"],"D435i Capture");st(tms["vit_ms"],"ViTPose");st(tms["total_ms"],"Per-frame total")
if tms["total_ms"]:print(f"\n  FPS: {len(tms['total_ms'])/REC_SEC:.1f}  有手帧: {sum(1 for h in tms['hand_cnt'] if h>0)}/{len(tms['hand_cnt'])}")
json.dump(tms,open(str(OUT/"report.json"),"w"),indent=2);print(f"报告: {OUT/'report.json'}\n"+"="*60)
