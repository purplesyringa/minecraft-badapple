import os
import json
from PIL import Image, ImageDraw


ROOT = "/baka/minecraft/resourcepacks/Bad Apple!!/assets"
COLORS = [0, 9, 26, 49, 75, 105, 139, 174, 213, 255]


os.makedirs(f"{ROOT}/minecraft/blockstates")
os.makedirs(f"{ROOT}/badapple/models/block")
os.makedirs(f"{ROOT}/badapple/textures/block")


with open("opaqueblocks") as f:
    for i, name in enumerate(f):
        name = name.strip()
        if i == len(COLORS) ** 2:
            break

        with open(f"{ROOT}/minecraft/blockstates/{name}.json", "w") as f1:
            json.dump({
                "variants": {
                    "": {
                        "model": f"badapple:block/{name}"
                    }
                }
            }, f1)

        with open(f"{ROOT}/badapple/models/block/{name}.json", "w") as f1:
            json.dump({
                "ambientocclusion": False,
                "elements": [
                    {
                        "from": [0, 0, 16],
                        "to": [8, 16, 16],
                        "faces": {
                            "south": {"texture": "#front"}
                        }
                    },
                    {
                        "from": [0, 0, 0],
                        "to": [16, 16, 0],
                        "faces": {
                            "north": {"texture": "#back"}
                        }
                    }
                ],
                "textures": {
                    "front": f"badapple:block/{name}",
                    "back": "minecraft:block/cobblestone"
                }
            }, f1)

        im = Image.new("L", (16, 16))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, 15, 7), fill=COLORS[i % len(COLORS)])
        draw.rectangle((0, 8, 15, 15), fill=COLORS[i // len(COLORS)])
        im.save(f"{ROOT}/badapple/textures/block/{name}.png", "PNG")


with open("transparentblocks") as f:
    for i, name in enumerate(f):
        name = name.strip()
        if i == len(COLORS) ** 2:
            break

        with open(f"{ROOT}/minecraft/blockstates/{name}.json", "w") as f1:
            json.dump({
                "variants": {
                    "": {
                        "model": f"badapple:block/{name}"
                    }
                }
            }, f1)

        with open(f"{ROOT}/badapple/models/block/{name}.json", "w") as f1:
            json.dump({
                "ambientocclusion": False,
                "elements": [
                    {
                        "from": [8, 0, 0],
                        "to": [16, 16, 0],
                        "faces": {
                            "south": {"texture": "#back"}
                        }
                    }
                ],
                "textures": {
                    "back": f"badapple:block/{name}"
                }
            }, f1)

        im = Image.new("L", (16, 16))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, 15, 7), fill=COLORS[i % len(COLORS)])
        draw.rectangle((0, 8, 15, 15), fill=COLORS[i // len(COLORS)])
        im.save(f"{ROOT}/badapple/textures/block/{name}.png", "PNG")


with open("commonsuperpixels.json") as f:
    common_super_pixels = json.load(f)


with open("commonblocks") as f:
    for super_pixel, name in zip(common_super_pixels, f):
        name = name.strip()

        with open(f"{ROOT}/minecraft/blockstates/{name}.json", "w") as f1:
            json.dump({
                "variants": {
                    "": {
                        "model": f"badapple:block/{name}"
                    }
                }
            }, f1)

        with open(f"{ROOT}/badapple/models/block/{name}.json", "w") as f1:
            json.dump({
                "ambientocclusion": False,
                "elements": [
                    {
                        "from": [0, 0, 0],
                        "to": [16, 16, 16],
                        "faces": {
                            "north": {"texture": "#back"},
                            "south": {"texture": "#front"}
                        }
                    }
                ],
                "textures": {
                    "front": f"badapple:block/{name}",
                    "back": "minecraft:block/cobblestone"
                }
            }, f1)

        im = Image.new("L", (16, 16))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, 7, 7), fill=super_pixel[0])
        draw.rectangle((0, 8, 7, 15), fill=super_pixel[1])
        draw.rectangle((8, 0, 15, 7), fill=super_pixel[2])
        draw.rectangle((8, 8, 15, 15), fill=super_pixel[3])
        im.save(f"{ROOT}/badapple/textures/block/{name}.png", "PNG")
