from .config import *

def snapVertex(p: RAW_POINT_TYPE, grid_size: float) -> RAW_POINT_TYPE:
    """ 將點座標貼齊格子點 """
    if grid_size > 0:
        return (int(round(p[0] / grid_size)), int(round(p[1] / grid_size)))
    else:
        return p

def unsnapVertex(snapP: RAW_POINT_TYPE, grid_size: float) -> RAW_POINT_TYPE:
    """ 將點座標從格子點移回來 """
    if grid_size > 0:
        return (snapP[0] * grid_size, snapP[1] * grid_size)
    else:
        return snapP

def snapEdges(edges: list[RAW_EDGE_TYPE], grid_size: float) -> list[RAW_EDGE_TYPE]:
    return [(snapVertex(p1, grid_size), snapVertex(p2, grid_size)) for (p1, p2) in edges]

def unsnapEdges(edges: list[RAW_EDGE_TYPE], grid_size: float) -> list[RAW_EDGE_TYPE]:
    return [(unsnapVertex(p1, grid_size), unsnapVertex(p2, grid_size)) for (p1, p2) in edges]
