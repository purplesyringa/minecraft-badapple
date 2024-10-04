from collections import defaultdict
import dataclasses
import itertools
import json
import os
from PIL import Image
import shutil
from typing import Optional


NBT = dict[str, str]
BlockState = tuple[str, NBT]
EquivalentBlockStates = list[BlockState]
Catalogue = list[tuple[EquivalentBlockStates, bool]]


def parse_catalogue(data: str) -> Catalogue:
    catalogue = []

    for line in data.splitlines():
        block_groups = line.partition("//")[0].split()
        if not block_groups:
            continue
        states = json.loads(block_groups.pop())

        is_see_through = block_groups[0] == "[seethrough]"
        if is_see_through:
            block_groups.pop(0)

        for values in itertools.product(*states.values()):
            state = dict(zip(states.keys(), values))
            for equivalent_blocks in block_groups:
                catalogue.append((
                    [(block, state) for block in equivalent_blocks.split("/")],
                    is_see_through
                ))

    return catalogue


with open("config.json") as f:
    config = json.load(f)
    assets_root = config["assets_root"]
    subpixels_width = config["subpixels"]["width"]
    subpixels_height = config["subpixels"]["height"]


with open("subpixel_predictions.json") as f:
    predictions: list[dict[tuple[tuple[int, int, int]], list[list[int]]]] = [{} for _ in range(3)]
    for z, z_predictions in enumerate(json.load(f)):
        for prediction in z_predictions:
            key = tuple(map(tuple, prediction["from"]))
            predictions[z][key] = prediction["to"]


catalogue_by_kind: dict[str, Catalogue] = {}

for kind in ["opaque", "transparent"]:
    with open(f"independent_{kind}.json") as f:
        catalogue_by_kind[kind] = parse_catalogue(f.read())[::-1]


for relative_path in [
    "minecraft/atlases",
    "minecraft/blockstates",
    "minecraft/models",
    "minecraft/textures"
]:
    path = f"{assets_root}/{relative_path}"
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    os.makedirs(path)


subpixels_by_z: list[tuple[int, int]] = [[] for _ in range(4)]
for y, row in enumerate(config["subpixels"]["distribution"]):
    for x, z in enumerate(row):
        subpixels_by_z[z].append((x, y))


def create_model(
    name: str,
    z: int,
    has_prediction: bool,
    rectangles: list[tuple[float, float, float, float]],
    x_border: list[tuple[float, float, float, bool]],
    y_border: list[tuple[float, float, float, bool]]
):
    dz = (2 - z) * 16

    model_description = {
        "ambientocclusion": False,
        "elements": []
    }

    for x1, y1, x2, y2 in rectangles:
        model_description["elements"].append({
            "from": [x1, y1, dz + (0 if z == 0 else 0.5)],
            "to": [x2, y2, dz + (0 if z == 0 else 0.5)],
            "shade": False,
            "faces": {
                "south": {"texture": "#t"}
            }
        })

    if z > 0:
        one = 16 / subpixels_width
        for x, y1, y2, is_positive in x_border:
            if is_positive:
                direction = "west"
                tx = x + one / 2
            else:
                direction = "east"
                tx = x - one / 2
            model_description["elements"].append({
                "from": [x, 16 - y2, dz],
                "to": [x, 16 - y1, dz + 0.5],
                "shade": False,
                "faces": {
                    direction: {
                        "texture": "#t",
                        "uv": [tx, y1, tx, y2]
                    }
                }
            })

        one = 16 / subpixels_height
        for y, x1, x2, is_positive in y_border:
            if is_positive:
                direction = "up"
                ty = y + one / 2
            else:
                direction = "down"
                ty = y - one / 2
            model_description["elements"].append({
                "from": [x1, 16 - y, dz],
                "to": [x2, 16 - y, dz + 0.5],
                "shade": False,
                "faces": {
                    direction: {
                        "texture": "#t",
                        "uv": [x1, ty, x2, ty]
                    }
                }
            })

    if z > 0 and has_prediction:
        model_description["elements"] += [
            {
                "from": [0, 0, dz - 0.5],
                "to": [16, 16, dz - 0.5],
                "shade": False,
                "faces": {
                    "south": {"texture": "#p"}
                }
            },
            {
                "from": [0, 0, dz - 0.5],
                "to": [0, 16, dz],
                "shade": False,
                "faces": {
                    "east": {
                        "texture": "#p",
                        "uv": [8 / subpixels_width, 0, 8 / subpixels_width, 16]
                    }
                }
            },
            {
                "from": [16, 0, dz - 0.5],
                "to": [16, 16, dz],
                "shade": False,
                "faces": {
                    "west": {
                        "texture": "#p",
                        "uv": [16 - 8 / subpixels_width, 0, 16 - 8 / subpixels_width, 16]
                    }
                }
            },
            {
                "from": [0, 16, dz - 0.5],
                "to": [16, 16, dz],
                "shade": False,
                "faces": {
                    "down": {
                        "texture": "#p",
                        "uv": [0, 8 / subpixels_height, 16, 8 / subpixels_height]
                    }
                }
            },
            {
                "from": [0, 0, dz - 0.5],
                "to": [16, 0, dz],
                "shade": False,
                "faces": {
                    "up": {
                        "texture": "#p",
                        "uv": [0, 16 - 8 / subpixels_height, 16, 16 - 8 / subpixels_height]
                    }
                }
            }
        ]

    with open(f"{assets_root}/minecraft/models/{name}.json", "w") as f:
        json.dump(model_description, f, separators=(",", ":"))


def detect_x_border(grid: list[list[bool]]) -> list[tuple[float, float, float, bool]]:
    width = len(grid[0])
    height = len(grid)
    sx = 16 / width
    sy = 16 / height
    border: list[tuple[float, float, float, bool]] = []
    for x in range(width):
        for key, ys in itertools.groupby(range(height), key=lambda y: (x == 0 or not grid[y][x - 1]) and grid[y][x]):
            if not key:
                continue
            ys = list(ys)
            y1 = ys[0]
            y2 = ys[-1] + 1
            border.append((x * sx, y1 * sy, y2 * sy, True))
        for key, ys in itertools.groupby(range(height), key=lambda y: grid[y][x] and (x + 1 == width or not grid[y][x + 1])):
            if not key:
                continue
            ys = list(ys)
            y1 = ys[0]
            y2 = ys[-1] + 1
            border.append(((x + 1) * sx, y1 * sy, y2 * sy, False))
    return border


Color = list[int]

@dataclasses.dataclass
class RenderRule:
    z: int
    subpixel_colors: list[Color]
    prediction: Optional[list[tuple[int, int, int]]]
    blockstates: EquivalentBlockStates

next_id = 0
block_to_variants: defaultdict[str, list[tuple[NBT, str]]] = defaultdict(list)
render_rules: list[RenderRule] = []
all_xy: list[tuple[int, int]] = [
    (x, y)
    for y in range(subpixels_height)
    for x in range(subpixels_width)
]

all_rectangles: list[tuple[float, float, float, float]] = [(0, 0, 16, 16)]
all_x_border: list[tuple[float, float, float, bool]] = [(0, 0, 16, True), (16, 0, 16, False)]
all_y_border: list[tuple[float, float, float, bool]] = [(0, 0, 16, True), (16, 0, 16, False)]

@dataclasses.dataclass
class Texture:
    name: str
    subpixels: list[tuple[int, int]]
    colors: list[tuple[int, int, int]]
    is_see_through: bool

textures: list[Texture] = []

for z, subpixels in enumerate(subpixels_by_z):
    kind = "opaque" if z == 0 else "transparent"
    catalogue = catalogue_by_kind[kind]

    grid = [[False] * subpixels_width for _ in range(subpixels_height)]
    transposed_grid = [[False] * subpixels_height for _ in range(subpixels_width)]
    for x, y in subpixels:
        grid[y][x] = True
        transposed_grid[x][y] = True

    # Find borders
    x_border = detect_x_border(grid)
    y_border = detect_x_border(transposed_grid)

    # Split subpixels into rectangles
    rectangles: list[tuple[float, float, float, float]] = []
    for y1 in range(subpixels_height):
        for x1 in range(subpixels_width):
            if not grid[y1][x1]:
                continue
            x2 = x1 + 1
            while x2 < subpixels_width and grid[y1][x2]:
                x2 += 1
            y2 = y1 + 1
            while y2 < subpixels_height and all(grid[y2][x1:x2]):
                y2 += 1
            for y in range(y1, y2):
                for x in range(x1, x2):
                    grid[y][x] = False
            rectangles.append((
                x1 / subpixels_width * 16,
                (1 - y2 / subpixels_height) * 16,
                x2 / subpixels_width * 16,
                (1 - y1 / subpixels_height) * 16
            ))

    if z == 0:
        create_model(f"f{z}", z, False, all_rectangles, all_x_border, all_y_border)
    elif z == 3:
        create_model(f"b{z}", z, False, rectangles, x_border, y_border)
    else:
        create_model(f"b{z}", z, False, rectangles, x_border, y_border)
        create_model(f"p{z}", z, True, rectangles, x_border, y_border)

    for subpixel_colors in itertools.product(config["colors"], repeat=len(subpixels)):
        key = tuple(map(tuple, subpixel_colors))
        prediction = None if z == 3 else predictions[z].get(key)

        model_location = f"m{next_id}"

        blockstates, is_see_through = catalogue.pop()
        filtered_blockstates = []
        for (block, state) in blockstates:
            block_to_variants[block].append((state, model_location))
            filtered_blockstates.append((
                block,
                {
                    key: value
                    for key, value
                    in state.items()
                    if not value.startswith("?")
                }
            ))
        render_rules.append(RenderRule(z, subpixel_colors, prediction, filtered_blockstates))

        if z == 0:
            prefix = "f"
        else:
            prefix = "bp"[bool(prediction)]

        model_description = {
            "parent": f"{prefix}{z}",
            "textures": {}
        }

        texture_subpixels = all_xy if z == 0 and prediction else subpixels
        texture_colors = prediction if z == 0 and prediction else subpixel_colors
        textures.append(Texture(f"t{next_id}", texture_subpixels, texture_colors, is_see_through))
        model_description["textures"]["t"] = f"t{next_id}"

        if z > 0 and prediction:
            textures.append(Texture(f"p{next_id}", all_xy, prediction, is_see_through))
            model_description["textures"]["p"] = f"p{next_id}"

        with open(f"{assets_root}/minecraft/models/m{next_id}.json", "w") as f:
            json.dump(model_description, f, separators=(",", ":"))

        next_id += 1


with open("render_rules.json", "w") as f:
    json.dump([dataclasses.asdict(rule) for rule in render_rules], f)


for block, variants in block_to_variants.items():
    blockstates_description = {
        "variants": {
            ",".join(f"{key}={value.lstrip('?')}" for key, value in state.items()): {
                "model": model_location
            }
            for state, model_location in variants
        }
    }

    with open(f"{assets_root}/minecraft/blockstates/{block}.json", "w") as f:
        json.dump(blockstates_description, f, separators=(",", ":"))


im = Image.new("RGBA", (subpixels_width * len(textures), subpixels_height))
pix = im.load()

for i, texture in enumerate(textures):
    if not texture.is_see_through:
        for y in range(subpixels_height):
            for xs in range(subpixels_width):
                pix[x + i * subpixels_width, y] = (255, 0, 255, 255)
    for (x, y), color in zip(texture.subpixels, texture.colors):
        pix[x + i * subpixels_width, y] = tuple(color + [255])

im.save(f"{assets_root}/minecraft/textures/badapple.png")

atlas = {
    "sources": [
        {
            "type": "unstitch",
            "resource": "badapple",
            "divisor_x": len(textures),
            "divisor_y": 1,
            "regions": [
                {
                    "sprite": texture.name,
                    "x": i,
                    "y": 0,
                    "width": 1,
                    "height": 1
                }
                for i, texture in enumerate(textures)
            ]
        }
    ]
}

with open(f"{assets_root}/minecraft/atlases/blocks.json", "w") as f:
    json.dump(atlas, f, separators=(",", ":"))
