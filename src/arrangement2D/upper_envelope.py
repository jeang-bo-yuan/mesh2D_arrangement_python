from .config import RAW_EDGE_TYPE, RAW_POINT_TYPE
from . import config as cfg
from .arrangement2D import arrangement2D
from . import util

from shapely import Polygon, Point
import shapely
from shapely.strtree import STRtree
import numpy as np

import math

import time

def get_plane_equation(poly: Polygon) -> tuple[float, float, float, float]:
    """ 回傳 (a, b, c, d) 代表平面方程式 ax + by + cz + d = 0 """
    p0 = np.array(poly.exterior.coords[0], np.float64)
    p1 = np.array(poly.exterior.coords[1], np.float64)
    p2 = np.array(poly.exterior.coords[2], np.float64)

    a, b, c = np.cross(p1 - p0, p2 - p0)
    d = - np.dot([a, b, c], p0)

    return (float(a), float(b), float(c), float(d))

def point2D_solve_z(point: RAW_POINT_TYPE, equation: tuple[float, float, float, float]) -> float:
    """ 給定 (x, y) 和平面方程，求出 z """
    # z = -(ax + by + d) / c
    x, y = point
    a, b, c, d = equation
    return -(a * x + b * y + d) / c

def upper_envelope(polygons: list[Polygon], *, triangulate_first = True, buffer_size = 1e-15) -> list[Polygon]:
    """
    Upper Envelope : 輸入一堆 mesh 的面，找到數個 open surface 把這些輸入的面給蓋住。

    輸入的面假設 xy 平面為地面，z 軸為高度（和 shapely 一樣）。

    演算法：
    1. 將每個面投影到 xy 平面，並求出 mesh arrangement 2D
    2. 對 arrangement 結果的每個頂點，看它被輸入的哪些面給覆蓋（cover），然後投影回去。當一個頂點被多個面覆蓋（cover）時，投影到最高的點上。
    
    :param triangulate_first: 是否要先對每個輸入的 Polygon 做三角化（強烈建議開啟此選項，這樣在投影回去時才能較好計算每一面的平面方程式）
    :param buffer_size: 因為數值問題，在計算 mesh arrangement 時交點可能會偏離原直線一點點，導致 arrangement 的結果可能比原本輸入的三角面還要向外擴。
                        所以在把頂點投影回去時，把原本的每個平面在 XY 平面上都向外擴 buffer_size 的大小再做覆蓋（cover）檢測。

                        buffer_size 調大會把更多 arrangement 的面投影到同個平面上，結果「可能」會看起來更 low poly。
                        但是在遇到幾乎垂直的面時，反而會把旁邊的頂點拉到極端高的地方。
    """
    polygons = [P for P in polygons if P.area > 0]
    if triangulate_first:
        polygons = util.triangulate(polygons)

    # 取出每一面的 x y 座標
    edges : list[RAW_EDGE_TYPE] = []
    minZ = math.inf

    for poly in polygons:
        for i in range(1, len(poly.exterior.coords)):
            edges.append((
                poly.exterior.coords[i - 1][:2],    # 起點 xy
                poly.exterior.coords[i][:2]         # 終點 xy
            ))

            minZ = min(minZ, poly.exterior.coords[i][2])

    # Step 1. 做 Arrangement #############################################################################
    A = arrangement2D(edges)
    A = util.triangulate(A)
    
    if cfg.DEBUG:
        start_perf = time.perf_counter()
    # Step 2. 將 Arrangement 中的每個平面的頂點投影回 3 維 ################################################
    point_z_dict = dict()
    point_set = set()
    for a in A:
        for i in range(1, len(a.exterior.coords)):
            point_z_dict[a.exterior.coords[i]] = minZ
            point_set.add(a.exterior.coords[i])

    points = [Point(p) for p in point_set]
    tree = STRtree(points)
    for poly in polygons:
        equation = get_plane_equation(poly)

        poly_buffer = poly.buffer(buffer_size)
        shapely.prepare(poly_buffer)
        
        for i in tree.query(poly_buffer, predicate='covers'):
            point_co = points[i].coords[0]

            point_z_dict[point_co] = max(
                point_z_dict[point_co],
                point2D_solve_z(point_co, equation)
            )


    if cfg.DEBUG:
        end_perf = time.perf_counter()
        print(f"Project Vertex Height: {end_perf - start_perf}")
        start_perf = time.perf_counter()

    # Step 3. 建造結果 ###############################################################################
    result = []
    for a in A:
        exterior = []
        for co in a.exterior.coords:
            if co in point_z_dict.keys():
                exterior.append((co[0], co[1], point_z_dict[co]))
            else:
                exterior.append((co[0], co[1], minZ))

        result.append(Polygon(exterior))

    if cfg.DEBUG:
        end_perf = time.perf_counter()
        print(f"Construct Result: {end_perf - start_perf}")
    
    return result


