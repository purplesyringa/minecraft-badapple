from collections import defaultdict
import dataclasses
import itertools
import json
import os
from PIL import Image
import shutil


NBT = dict[str, str]
BlockState = tuple[str, NBT]
EquivalentBlockStates = list[BlockState]
Catalogue = list[EquivalentBlockStates]


def parse_catalogue(data: str) -> Catalogue:
    catalogue = []

    for line in data.splitlines():
        block_groups = line.partition("//")[0].split()
        if not block_groups:
            continue
        states = json.loads(block_groups.pop())

        for values in itertools.product(*states.values()):
            state = dict(zip(states.keys(), values))
            for equivalent_blocks in block_groups:
                catalogue.append([(block, state) for block in equivalent_blocks.split("/")])

    return catalogue


with open("config.json") as f:
    config = json.load(f)
    assets_root = config["assets_root"]


with open("subpixel_predictions.json") as f:
    predictions: dict[tuple[tuple[int, int, int]], list[list[int]]] = {}
    for prediction in json.load(f):
        key = tuple(map(tuple, prediction["from"]))
        predictions[key] = prediction["to"]


catalogue_by_kind: dict[str, Catalogue] = {}

for kind in ["opaque", "transparent"]:
    with open(f"independent_{kind}.json") as f:
        catalogue_by_kind[kind] = parse_catalogue(f.read())[::-1]


for relative_path in ["minecraft/blockstates", "badapple/models", "badapple/textures/block"]:
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


Color = list[int]

@dataclasses.dataclass
class RenderRule:
    z: int
    subpixel_colors: list[Color]
    blockstates: EquivalentBlockStates

next_id = 0
block_to_variants: defaultdict[str, list[tuple[NBT, str]]] = defaultdict(list)
render_rules: list[RenderRule] = []

for z, subpixels in enumerate(subpixels_by_z):
    kind = "opaque" if z == 0 else "transparent"
    catalogue = catalogue_by_kind[kind]

    for subpixel_colors in itertools.product(config["colors"], repeat=len(subpixels)):
        im = Image.new("RGBA", (config["subpixels"]["width"], config["subpixels"]["height"]))
        pix = im.load()
        if z == 0:
            key = tuple(map(tuple, subpixel_colors))
            prediction = predictions.get(key)
            if prediction:
                for (y, x), color in zip(
                    itertools.product(range(im.height), range(im.width)),
                    prediction
                ):
                    pix[x, y] = tuple(color + [255])
        for (x, y), color in zip(subpixels, subpixel_colors):
            pix[x, y] = tuple(color + [255])
        im.save(f"{assets_root}/badapple/textures/block/t{next_id}.png")

        dz = (2 - z) * 16 - (0.4 if z == 0 else 0)
        model_description = {
            "ambientocclusion": False,
            "elements": [
                {
                    "from": [0, 0, dz],
                    "to": [16, 16, dz],
                    "shade": False,
                    "faces": {
                        "south": {"texture": "#front"}
                    }
                }
            ],
            "textures": {
                "front": f"badapple:block/t{next_id}",
            }
        }
        with open(f"{assets_root}/badapple/models/m{next_id}.json", "w") as f:
            json.dump(model_description, f)
        model_location = f"badapple:m{next_id}"

        next_id += 1

        blockstates = catalogue.pop()
        for (block, state) in blockstates:
            block_to_variants[block].append((state, model_location))
        render_rules.append(RenderRule(z, subpixel_colors, blockstates))


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
        json.dump(blockstates_description, f)
