import igl
import arrangement2D.config as cfg
cfg.DEBUG = True
cfg.DEBUG_PLOT = True

from arrangement2D.arrangement2D import arrangement2D
from arrangement2D.snap import snapEdges

import os

def main():
    Vs, Fs = igl.read_triangle_mesh(os.path.join(os.path.dirname(__file__), "fitting.obj"))
    
    edges = []
    for face in Fs:
        v1 = Vs[face[0]]
        v2 = Vs[face[1]]
        v3 = Vs[face[2]]

        # 丟掉 y 軸（高度）
        edges.append([(v1[0], v1[2]), (v2[0], v2[2])])
        edges.append([(v2[0], v2[2]), (v3[0], v3[2])])
        edges.append([(v3[0], v3[2]), (v1[0], v1[2])])
    
    edges = snapEdges(edges, 1e-4)
    arrangement2D(edges)


if __name__ == "__main__":
    main()
