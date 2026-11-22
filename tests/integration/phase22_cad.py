"""Rasterize geometry from the project's OCC generator without a native viewport."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageColor
from OCC.Extend.DataExchange import write_stl_file
from OCC.Extend.TopologyUtils import list_of_shapes_to_compound
from osdagbridge.core.bridge_types.plate_girder.cad_generator import PlateGirderCADGenerator


def framing_plan(components):
    """Draw the CAD solids in plan with the deck transparent to the framing."""
    from matplotlib.figure import Figure
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Patch

    fig = Figure(figsize=(9, 3.6), layout="constrained")
    ax = fig.subplots()
    legend = []
    for key, color, label in (
        ("deck_slab", "#eef1f3", "Deck footprint"),
        ("cross_bracings", "#97734b", "Cross bracing"),
        ("girder_top_flanges", "#245779", "Girder top flanges"),
        ("crash_barriers", "#62676a", "Barriers"),
    ):
        faces = components.get(key)
        if faces is None:
            continue
        ax.add_collection(PolyCollection(faces[:, :, :2] / 1000, facecolors=color,
                                         edgecolors="none", antialiaseds=False))
        legend.append(Patch(facecolor=color, label=label))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlabel("Longitudinal position (m)")
    ax.set_ylabel("Transverse position (m)")
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 1.01),
              ncol=len(legend), frameon=False, fontsize=9)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    return buf.getvalue()


def cad_views(params):
    data = PlateGirderCADGenerator().generate(params)
    triangles, colors = [], []
    components = {}
    with TemporaryDirectory() as tmp:
        for key, color in (("girder_web", "#455d72"), ("girder_top_flanges", "#526d85"),
                           ("girder_bottom_flanges", "#526d85"), ("cross_bracings", "#857548"),
                           ("deck_slab", "#b8b7b1"), ("crash_barriers", "#777777")):
            shapes = data[key]
            if not isinstance(shapes, list):
                shapes = [shapes]
            if not shapes:
                continue
            shape, ok = list_of_shapes_to_compound(shapes)
            assert ok
            path = Path(tmp, key + ".stl")
            write_stl_file(shape, str(path), mode="binary")
            records = np.fromfile(path, offset=84, dtype=np.dtype([("normal","<f4",3),("v","<f4",(3,3)),("attr","<u2")]))
            components[key] = records["v"]
            triangles.extend(records["v"])
            colors.extend([color] * len(records))
    triangles = np.asarray(triangles)
    images = {"girder_top": framing_plan(components)}
    for key, normal, horiz in (("cross_section",[1,0,0],[0,1,0]),
                                ("final_geometry",[1,-2,1.2],[2,1,0])):
        normal = normal / np.linalg.norm(normal)
        horiz = horiz / np.linalg.norm(horiz)
        vert = np.cross(normal, horiz)
        projected = triangles @ np.stack([horiz, vert], axis=1)
        depth = triangles @ normal
        # Orthographic projection with a depth buffer so overlapping CAD faces
        # are visible only where they are nearest the camera.
        projected -= projected.min(axis=(0, 1))
        span = projected.max(axis=(0, 1))
        projected *= min(1350/span[0], 470/span[1])
        width, height = np.ceil(projected.max(axis=(0, 1))).astype(int) + 1
        raster = np.full((height, width, 3), 255, dtype=np.uint8)
        buffer = np.full((height, width), -np.inf)
        for pts, distances, color in zip(projected, depth, colors):
            a,b,c = pts
            den = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
            if abs(den) < 1e-8:
                continue
            xmin,ymin = np.floor(pts.min(axis=0)).astype(int)
            xmax,ymax = np.ceil(pts.max(axis=0)).astype(int)
            y,x = np.ogrid[ymin:ymax+1, xmin:xmax+1]
            u = ((b[1]-c[1])*(x-c[0]) + (c[0]-b[0])*(y-c[1])) / den
            v = ((c[1]-a[1])*(x-c[0]) + (a[0]-c[0])*(y-c[1])) / den
            w = 1-u-v
            z = u*distances[0] + v*distances[1] + w*distances[2]
            region = np.s_[ymin:ymax+1, xmin:xmax+1]
            draw = (u>=-1e-7) & (v>=-1e-7) & (w>=-1e-7) & (z>buffer[region])
            buffer[region][draw] = z[draw]
            raster[region][draw] = ImageColor.getrgb(color)
        buf = BytesIO()
        Image.fromarray(raster[::-1]).save(buf,format="PNG")
        images[key]=buf.getvalue()
    return images
