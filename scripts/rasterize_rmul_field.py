from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_IN,TopAbs_ON
from OCP.TopoDS import TopoDS
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from PIL import Image
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Convert official RMUL 2026 STEP to a horizontal occupancy slice')
parser.add_argument('step', help='Path to the official RMUL2026.stp')
args=parser.parse_args()
r=STEPControl_Reader();r.ReadFile(args.step);r.TransferRoots();shape=r.OneShape();ex=TopExp_Explorer(shape,TopAbs_SOLID);solid=TopoDS.Solid_s(ex.Current());classifier=BRepClass3d_SolidClassifier(solid)
w,h,res=252,172,.05
im=Image.new('L',(w,h),254)
for row in range(h):
 for col in range(w):
  x=-6300+(col+.5)*50;z=-4300+(row+.5)*50
  classifier.Perform(gp_Pnt(x,-20,z),1e-5)
  occupied=classifier.State() in (TopAbs_IN,TopAbs_ON)
  # The physical arena boundary is closed for the two-dimensional exercise.
  if occupied or row in (0,h-1) or col in (0,w-1):im.putpixel((col,h-1-row),0)
p=Path('src/rm_nav_training_lab/maps');im.save(p/'rmul2026_3v3.pgm')
(p/'rmul2026_3v3.yaml').write_text('image: rmul2026_3v3.pgm\nmode: trinary\nresolution: 0.05\norigin: [-6.3, -4.3, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
print('saved',im.size)
