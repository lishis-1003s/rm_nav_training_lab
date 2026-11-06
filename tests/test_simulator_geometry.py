"""Geometry and map regression tests; no running ROS graph is required."""
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from rm_nav_training_lab.simulator import TrainingSimulator, find_spawn

class GeometryTests(unittest.TestCase):
    def world(self):
        w = SimpleNamespace(map_width=40,map_height=40,map_resolution=.1,
            map_origin=(0.,0.),map_cells=[0]*1600,robot_radius=.3,
            obstacles={},faults={'dynamic_obstacle':False})
        w._occupied=lambda x,y: TrainingSimulator._occupied(w,x,y)
        return w

    def test_body_edge_collides_before_center(self):
        w=self.world()
        for row in range(40):w.map_cells[row*40+20]=100
        self.assertTrue(TrainingSimulator._clear_body(w,1.6,2.))
        self.assertFalse(TrainingSimulator._clear_body(w,1.8,2.))

    def test_obstacle_impacts_ray_and_body(self):
        w=self.world();w.obstacles={'one':{'x':2.,'y':2.,'radius':.3}}
        self.assertTrue(w._occupied(2.,2.))
        self.assertFalse(TrainingSimulator._clear_body(w,1.5,2.))
        self.assertTrue(TrainingSimulator._clear_body(w,1.3,2.))

    def test_outside_and_unknown_are_blocked(self):
        w=self.world();w.map_cells[20*40+20]=-1
        self.assertTrue(w._occupied(-.01,2.))
        self.assertTrue(w._occupied(2.05,2.05))
        self.assertFalse(TrainingSimulator._clear_body(w,.2,1.))

    def test_maps_use_metadata_and_have_valid_spawn(self):
        maps=Path(__file__).resolve().parents[1]/'src/rm_nav_training_lab/maps'
        for name,size,res in [('training_map',(120,120),.1),('rmul2026_3v3',(252,172),.05),('beginner_arena',(280,200),.05)]:
            data=TrainingSimulator._load_pgm(maps/(name+'.yaml'))
            self.assertEqual(data[:2],size);self.assertEqual(data[2],res)
            x,y=find_spawn(*data,.3)
            w=self.world();w.map_width,w.map_height,w.map_resolution,w.map_origin,w.map_cells=data
            self.assertTrue(TrainingSimulator._clear_body(w,x,y))

if __name__=='__main__':unittest.main()
