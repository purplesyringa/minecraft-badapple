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
    rectangles: list[tuple[float, float, float, float]]
):
    dz = (2 - z) * 16 + (0 if z == 0 else 0.6)

    model_description = {
        "ambientocclusion": False,
        "elements": []
    }

    for x1, y1, x2, y2 in rectangles:
        model_description["elements"].append({
            "from": [x1, y1, dz],
            "to": [x2, y2, dz],
            "shade": False,
            "faces": {
                "south": {"texture": "#t"}
            }
        })

    if z > 0 and has_prediction:
        model_description["elements"].append({
            "from": [0, 0, dz - 1.2],
            "to": [16, 16, dz - 1.2],
            "shade": False,
            "faces": {
                "south": {"texture": "#p"}
            }
        })

    with open(f"{assets_root}/minecraft/models/{name}.json", "w") as f:
        json.dump(model_description, f, separators=(",", ":"))


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

@dataclasses.dataclass
class Texture:
    name: str
    subpixels: list[tuple[int, int]]
    colors: list[tuple[int, int, int]]

textures: list[Texture] = []

for z, subpixels in enumerate(subpixels_by_z):
    kind = "opaque" if z == 0 else "transparent"
    catalogue = catalogue_by_kind[kind]

    # Split subpixels into rectangles
    rectangles: list[tuple[float, float, float, float]] = []
    grid = [[False] * subpixels_width for _ in range(subpixels_height)]
    for x, y in subpixels:
        grid[y][x] = True
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
        create_model(f"f{z}", z, False, [(0, 0, 16, 16)])
    elif z == 3:
        create_model(f"b{z}", z, False, rectangles)
        create_model(f"f{z}", z, False, [(0, 0, 16, 16)])
    else:
        create_model(f"b{z}", z, False, rectangles)
        create_model(f"f{z}", z, False, [(0, 0, 16, 16)])
        create_model(f"p{z}", z, True, rectangles)
        create_model(f"c{z}", z, True, [(0, 0, 16, 16)])

    for subpixel_colors in itertools.product(config["colors"], repeat=len(subpixels)):
        key = tuple(map(tuple, subpixel_colors))
        prediction = None if z == 3 else predictions[z].get(key)

        model_location = f"m{next_id}"

        blockstates, is_see_through = catalogue.pop()
        for (block, state) in blockstates:
            block_to_variants[block].append((state, model_location))
        render_rules.append(RenderRule(z, subpixel_colors, prediction, blockstates))

        if z == 0:
            prefix = "f"
        else:
            prefix = "bfpc"[bool(prediction) * 2 + is_see_through]

        model_description = {
            "parent": f"{prefix}{z}",
            "textures": {}
        }

        texture_subpixels = all_xy if z == 0 and prediction else subpixels
        texture_colors = prediction if z == 0 and prediction else subpixel_colors
        textures.append(Texture(f"t{next_id}", texture_subpixels, texture_colors))
        model_description["textures"]["t"] = f"t{next_id}"

        if z > 0 and prediction:
            textures.append(Texture(f"p{next_id}", all_xy, prediction))
            model_description["textures"]["p"] = f"p{next_id}"

        with open(f"{assets_root}/minecraft/models/m{next_id}.json", "w") as f:
            json.dump(model_description, f, separators=(",", ":"))

        next_id += 1


with open("render_rules.json", "w") as f:
    json.dump([dataclasses.asdict(rule) for rule in render_rules], f)


for block, variants in block_to_variants.items():
    blockstates_description = {
        "variants": {
            ",".join(f"{key}={value}" for key, value in state.items()): {
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
