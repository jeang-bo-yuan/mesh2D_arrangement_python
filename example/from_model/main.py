import igl
import arrangement2D.config as cfg
cfg.DEBUG = True
cfg.DEBUG_PLOT = True

from arrangement2D.arrangement2D import arrangement2D
from arrangement2D.snap import snapEdges
from arrangement2D.util import triangulate

from shapely.plotting import plot_polygon
from shapely import to_wkt
import matplotlib.pyplot as plt

import tkinter as tk

import os

def main():
    Vs, Fs = igl.read_triangle_mesh(os.path.join(os.path.dirname(__file__), "project_face_fail.obj"))
    
    edges = []
    for face in Fs:
        v1 = Vs[face[0]]
        v2 = Vs[face[1]]
        v3 = Vs[face[2]]

        # 丟掉 y 軸（高度）
        edges.append([(v1[0], v1[2]), (v2[0], v2[2])])
        edges.append([(v2[0], v2[2]), (v3[0], v3[2])])
        edges.append([(v3[0], v3[2]), (v1[0], v1[2])])
    
    # edges = snapEdges(edges, 1e-4)
    A = triangulate(arrangement2D(edges))

    plt.title("Arrangemet (Triangulated)")
    wkt = ""
    print("\n\nArrangement to WKT")
    for p in A:
        plot_polygon(p)
        wkt += (to_wkt(p) + '\n')
    plt.show(block=False)

    showWKT(wkt)

def showWKT(wkt: str):
    root = tk.Tk()
    root.title("WKT")
    root.geometry("=400x300+100+100")

    # 設定 grid 的權重
    # row 0 (文字區) 權重為 1，代表它會吃掉所有剩餘空間
    root.grid_rowconfigure(0, weight=1)
    # column 0 權重為 1，代表水平填滿
    root.grid_columnconfigure(0, weight=1)
    
    # --- 上半部：文字區域與捲軸 ---
    frame_top = tk.Frame(root)
    frame_top.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    # 建立捲軸
    scrollbar = tk.Scrollbar(frame_top)
    scrollbar.pack(side="right", fill="y")

    # 建立多行文字框，並連結捲軸
    text_area = tk.Text(frame_top, yscrollcommand=scrollbar.set, font=("Microsoft JhengHei", 10))
    text_area.pack(side="left", expand=True, fill="both")
    scrollbar.config(command=text_area.yview)

    # 設定文字
    text_area.insert("1.0", wkt)
    text_area.config(state='disabled')

    def copy_to_clipboard():
        # 清除剪貼簿並寫入新內容
        root.clipboard_clear()
        root.clipboard_append(wkt)
        
        # 彈出小提醒（選配）
        print("WKT 已複製到剪貼簿！")

    # --- 下半部：按鈕 ---
    btn_copy = tk.Button(root, text="複製文字", command=copy_to_clipboard, bg="#4CAF50", fg="white", pady=5)
    btn_copy.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    root.mainloop()


if __name__ == "__main__":
    main()
