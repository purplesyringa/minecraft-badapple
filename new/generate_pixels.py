from collections import defaultdict
import dataclasses
import itertools
import json
import os
from PIL import Image
import shutil


with open("config.json") as f:
    config = json.load(f)
    assets_root = config["assets_root"]
    pixel_width = config["pixel"]["width"]
    pixel_height = config["pixel"]["height"]
    superpixel_width = config["superpixel"]["width"]
    superpixel_height = config["superpixel"]["height"]
    pixel_size = pixel_width * pixel_height


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

        is_see_through = block_groups[0] == "[seethrough]"
        if is_see_through:
            block_groups.pop(0)

        for values in itertools.product(*states.values()):
            state = dict(zip(states.keys(), values))
            for equivalent_blocks in block_groups:
                catalogue.append([(block, state) for block in equivalent_blocks.split("/")])

    return catalogue

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


model_description = {
    "ambientocclusion": False,
    "elements": [
        {
            "from": [0, 0, 0],
            "to": [16, 16, 16],
            "shade": False,
            "faces": {
                "south": {"texture": "#t"},
                "north": {"texture": "#c"}
            }
        }
    ],
    "textures": {
        "c": "block/cobblestone"
    }
}

with open(f"{assets_root}/minecraft/models/p.json", "w") as f:
    json.dump(model_description, f)


model_description = {
    "ambientocclusion": False,
    "elements": [
        {
            "from": [0, 16 * (1 - superpixel_height // pixel_height), 0],
            "to": [16 * superpixel_width // pixel_width, 16, 16],
            "shade": False,
            "faces": {
                "south": {
                    "uv": [0, 0, 16, 16],
                    "texture": "#t"
                },
                "north": {
                    "uv": [0, 0, 16, 16],
                    "texture": "#c"
                }
            }
        }
    ],
    "textures": {
        "c": "block/cobblestone"
    }
}

with open(f"{assets_root}/minecraft/models/s.json", "w") as f:
    json.dump(model_description, f)


Color = tuple[int, int, int]

@dataclasses.dataclass
class Texture:
    name: str
    subpixel_colors: tuple[Color]

block_to_variants: defaultdict[str, list[tuple[NBT, str]]] = defaultdict(list)


pixel_render_rules: list[EquivalentBlockStates] = []
pixel_textures: list[Texture] = []

for texture_id, subpixel_colors in enumerate(itertools.product(map(tuple, config["colors"]), repeat=pixel_size)):
    blockstates = catalogue_by_kind["opaque"].pop()
    filtered_blockstates = []
    for block, state in blockstates:
        block_to_variants[block].append((state, f"p{texture_id}"))
        filtered_blockstates.append((
            block,
            {key: value for key, value in state.items() if not value.startswith("?")}
        ))
    pixel_render_rules.append(filtered_blockstates)

    model_description = {
        "parent": "p",
        "textures": {
            "t": f"p{texture_id}"
        }
    }

    pixel_textures.append(Texture(f"p{texture_id}", subpixel_colors))

    with open(f"{assets_root}/minecraft/models/p{texture_id}.json", "w") as f:
        json.dump(model_description, f, separators=(",", ":"))


Color = tuple[int, int, int]

superpixel_render_rules: list[EquivalentBlockStates] = []
superpixel_textures: list[Texture] = []

with open("superpixel_predictions.json") as f:
    superpixel_predictions = json.load(f)

for texture_id, subpixel_colors_value in enumerate(superpixel_predictions):
    subpixel_colors: list[Color] = []
    for y in range(superpixel_height - 1, -1, -1):
        for x in range(superpixel_width - 1, -1, -1):
            color_id = subpixel_colors_value % len(config["colors"])
            subpixel_colors_value //= len(config["colors"])
            color = tuple(config["colors"][color_id])
            subpixel_colors.append(color)
    subpixel_colors.reverse()

    blockstates = catalogue_by_kind["opaque"].pop()
    filtered_blockstates = []
    for block, state in blockstates:
        block_to_variants[block].append((state, f"s{texture_id}"))
        filtered_blockstates.append((
            block,
            {key: value for key, value in state.items() if not value.startswith("?")}
        ))
    superpixel_render_rules.append(filtered_blockstates)

    model_description = {
        "parent": "s",
        "textures": {
            "t": f"s{texture_id}"
        }
    }

    superpixel_textures.append(Texture(f"s{texture_id}", subpixel_colors))

    with open(f"{assets_root}/minecraft/models/s{texture_id}.json", "w") as f:
        json.dump(model_description, f, separators=(",", ":"))


with open("render_rules.json", "w") as f:
    json.dump({
        "pixel": pixel_render_rules,
        "superpixel": superpixel_render_rules
    }, f)


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


atlas = {"sources": []}

def make_textures(name: str, width: int, height: int, textures: list[Texture]):
    im = Image.new("RGBA", (width * len(textures), height))
    pix = im.load()

    for i, texture in enumerate(textures):
        for y in range(height):
            for x in range(width):
                color = texture.subpixel_colors[y * width + x]
                pix[x + i * width, y] = color + (255,)

    im.save(f"{assets_root}/minecraft/textures/{name}.png")

    atlas["sources"].append({
        "type": "unstitch",
        "resource": name,
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
    })


make_textures("pixels", pixel_width, pixel_height, pixel_textures)
make_textures("superpixels", superpixel_width, superpixel_height, superpixel_textures)

with open(f"{assets_root}/minecraft/atlases/blocks.json", "w") as f:
    json.dump(atlas, f, separators=(",", ":"))
