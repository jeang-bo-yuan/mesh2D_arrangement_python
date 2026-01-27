import igl
import arrangement2D.config as cfg
cfg.DEBUG = True
cfg.DEBUG_PLOT = True

from arrangement2D.upper_envelope import upper_envelope
from arrangement2D.snap import snapEdges

from shapely import Polygon
import numpy as np

import os

#region 輸入 ###################################################################
INPUT_OBJ = "fitting.obj"
INPUT_PATH = os.path.join(os.path.dirname(__file__), INPUT_OBJ)
OUTPUT_OBJ = f"upper_envelope/{INPUT_OBJ}"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), OUTPUT_OBJ)





#region Main #####################################################################################
def main():
    Vs, Fs = igl.read_triangle_mesh(INPUT_PATH)

    # Obj 檔假設 Y 軸為高度，而 shapely 假設 Z 軸為高度
    polygons = []
    for face in Fs:
        v1 = swapYZ(Vs[face[0]])
        v2 = swapYZ(Vs[face[1]])
        v3 = swapYZ(Vs[face[2]])

        polygons.append(Polygon((v1, v2, v3)))
    
    polygons = upper_envelope(polygons)

    output_obj(polygons)




#region Helper #################################################################
def swapYZ(v: tuple[float, float, float]):
    return (v[0], v[2], v[1]) 

def output_obj(polygons: list[Polygon]):
    # N = len(polygons)
    Vs = [] # N * 3, 頂點座標
    Fs = [] # N * 3, 每一面的 index

    vertex_index_lookup = dict()

    def get_vertex_index(v):
        if v in vertex_index_lookup.keys():
            return vertex_index_lookup[v]
        else:
            Vs.append(v)
            vertex_index_lookup[v] = len(Vs) - 1
            return len(Vs) - 1

    for poly in polygons:
        v1 = swapYZ(poly.exterior.coords[0])
        v2 = swapYZ(poly.exterior.coords[1])
        v3 = swapYZ(poly.exterior.coords[2])

        Fs.append((get_vertex_index(v1), get_vertex_index(v2), get_vertex_index(v3)))
    
    igl.write_triangle_mesh(OUTPUT_PATH, np.array(Vs), np.array(Fs))


if __name__ == "__main__":
    main()


