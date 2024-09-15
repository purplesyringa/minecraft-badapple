from PIL import Image
from collections import defaultdict
import json
import os
import sys

WIDTH = 128
HEIGHT = 96

last_frame = [[None] * HEIGHT for _ in range(WIDTH)]

vertices = []
vertex_to_id = {}

def get_vertex(v):
    if v not in vertex_to_id:
        vertex_to_id[v] = len(vertices)
        vertices.append(v)
    return vertex_to_id[v]

edges = defaultdict(int)

for frame_num, frame in enumerate(sorted(os.listdir("frames"))):
    if frame_num % 10 == 0:
        print("Frame", frame_num, file=sys.stderr)

    im = Image.open(f"frames/{frame}")
    pix = im.load()
    assert im.width == WIDTH * 2
    assert im.height == HEIGHT * 2

    for x in range(WIDTH):
        for y in range(HEIGHT):
            pixel = tuple(pix[x * 2 + dx, y * 2 + dy] for dx in range(2) for dy in range(2))
            if last_frame[x][y] == pixel:
                continue
            if frame_num > 0:
                a, b = get_vertex(last_frame[x][y]), get_vertex(pixel)
                if a > b:
                    a, b = b, a
                edges[a, b] += 1
            last_frame[x][y] = pixel

print(json.dumps({
    "vertices": [list(pixel) for pixel in vertices],
    "edges": [[a, b, w] for (a, b), w in edges.items()]
}))
