from .config import RAW_EDGE_TYPE, RAW_POINT_TYPE
from . import config as cfg
from .arrangement2D import arrangement2D
from . import util

from shapely import Polygon, Point
import shapely
from shapely.strtree import STRtree
import numpy as np

import math
from typing import Literal
from collections import defaultdict
import time

#region Utility
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
#endregion

#region Upper Envelope
def upper_envelope(polygons: list[Polygon], *, triangulate_first = True, buffer_size = 1e-15, project_method: Literal['VERTEX', 'FACE'] = 'VERTEX') -> list[Polygon]:
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
    
    if project_method == 'VERTEX':
        return project_vertex(polygons, A, buffer_size, minZ)
    elif project_method == 'FACE':
        return project_face(polygons, A, buffer_size, minZ)
    
    raise ValueError(f"Unknown project method: {project_method}")

def project_vertex(polygons: list[Polygon], A: list[Polygon], buffer_size: float, minZ: float):
    """
    將 A 的每個頂點投影回 polygons 中最高的位置    
    """
    if cfg.DEBUG:
        start_perf = time.perf_counter()
        print("== Upper Envelope Project Vertex ==")
        print(f"\t#Arrangement / #Polygons: {len(A)} / {len(polygons)}")
    # Step 2. 將 Arrangement 中的每個平面的頂點投影回 3 維 ################################################
    point_z_dict = dict()
    point_set = set()
    # 先記錄所有頂點
    for a in A:
        for i in range(1, len(a.exterior.coords)):
            point_z_dict[a.exterior.coords[i]] = minZ # 該頂點預設投回 minZ
            point_set.add(a.exterior.coords[i])

    points = [Point(p) for p in point_set]
    tree = STRtree(points)
    # 對於每個原始的面
    for poly in polygons:
        equation = get_plane_equation(poly)

        poly_buffer = poly.buffer(buffer_size)
        shapely.prepare(poly_buffer)
        
        # 看它蓋住哪些點
        for i in tree.query(poly_buffer, predicate='covers'):
            point_co = points[i].coords[0]

            # 將這些點投影回該面並記錄最大值
            point_z_dict[point_co] = max(
                point_z_dict[point_co],
                point2D_solve_z(point_co, equation)
            )

    if cfg.DEBUG:
        end_perf = time.perf_counter()
        print(f"Project Vertex Height: {end_perf - start_perf} s")
        start_perf = time.perf_counter()

    # Step 3. 建造結果 ###############################################################################
    result = []
    for a in A:
        exterior = []
        for co in a.exterior.coords:
            exterior.append((co[0], co[1], point_z_dict[co]))

        result.append(Polygon(exterior))

    if cfg.DEBUG:
        end_perf = time.perf_counter()
        print(f"Construct Result: {end_perf - start_perf} s")

    return result

def project_face(polygons: list[Polygon], A: list[Polygon], buffer_size: float, minZ: float):
    """
    對於 A 中每一面投影回 polygons 中最高的
    """
    result = []

    if cfg.DEBUG:
        start_perf = time.perf_counter()
        print("== Upper Envelope Project Face ==")
        print(f"\t#Arrangement / #Polygons: {len(A)} / {len(polygons)}")
        project_fail = 0

    # Step 2. Project Face and Record Vertex Height ######################################################
    # 給一個 (x, y) -> 一個列表包含所有高度
    vertex_height_list: defaultdict[cfg.RAW_POINT_TYPE, list[float]] = defaultdict(list)

    # 所有原始的面
    tree = STRtree([P.buffer(buffer_size) for P in polygons])
    
    # 結果
    result: list[Polygon] = []

    for arrangement in A:
        # 最好的投影、最好的投影的高度
        best_proj = [(co[0], co[1], minZ) for co in arrangement.exterior.coords]
        best_height = minZ

        # 找出被原始的哪些面覆蓋
        for i in tree.query(arrangement, predicate='covered_by'):
            plane_eq = get_plane_equation(polygons[i])
            
            # 實際投影一次
            proj = [(co[0], co[1], point2D_solve_z(co, plane_eq)) for co in arrangement.exterior.coords]
            height = sum(co[2] for co in proj) / len(proj) # 平均高度

            # 若更高
            if height > best_height:
                best_proj = proj
                best_height = height
        pass

        if best_height == minZ:
            # print(f"Project Fail: {best_proj}")
            project_fail += 1
        
        # 對每個 vertex 看那個 (x, y) 是否有其他 a 投影過，如果有而且 z 差距小於 1e-4 則使用它
        # 做這步的用意：即使相鄰兩面原本是連起來的，但經過計算得到投影的 z 值可能會和原本的值有誤差
        for i, vert in enumerate(best_proj):
            do_snap = False

            for z in vertex_height_list[vert[:2]]:
                if abs(vert[2] - z) < 1e-4:
                    best_proj[i] = vert[:2] + (z,)
                    do_snap = True
                    break

            # 記錄 z 值
            if not do_snap:
                vertex_height_list[vert[:2]].append(vert[2])
        
        result.append(Polygon(best_proj))

    if cfg.DEBUG:
        end_perf = time.perf_counter()
        print(f"\t#Project Failed: {project_fail}")
        print(f"Project Face Height: {end_perf - start_perf} s")

    return result
#endregion
