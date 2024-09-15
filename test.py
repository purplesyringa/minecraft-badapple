import nbtlib
from nbtlib import File, Compound, List, Int, String, Byte, Long, Float
from PIL import Image
import os
import json

ROOT = "/baka/minecraft/saves/Bad Apple!!/generated/badapple/structures"
STRUCTURE_SIZE = 48
VERSION = 1
WIDTH = 128
HEIGHT = 96
DEPTH = 5
COLORS = [0, 9, 26, 49, 75, 105, 139, 174, 213, 255]

with open("opaqueblocks") as f:
    opaque_blocks = [name.strip() for name in f]
with open("transparentblocks") as f:
    transparent_blocks = [name.strip() for name in f]
d_blocks = [opaque_blocks, transparent_blocks]

with open("commonblocks") as f:
    common_blocks = [name.strip() for name in f]
with open("commonsuperpixels.json") as f:
    common_super_pixels = {tuple(pixel): i for i, pixel in enumerate(json.load(f))}

last_frame = [[[""] * HEIGHT for _ in range(WIDTH)] for _ in range(2)]

frames = sorted(os.listdir("frames"))

for frame_num in range(len(frames) + 2):
    if frame_num % 10 == 0:
        print("Frame", frame_num)

    i = frame_num // 2 % 2
    j = frame_num % 2

    if frame_num < len(frames):
        im = Image.open(f"frames/{frames[frame_num]}")
        pix = im.load()
        assert im.width == WIDTH * 2
        assert im.height == HEIGHT * 2

    for sx in range((WIDTH + STRUCTURE_SIZE - 1) // STRUCTURE_SIZE):
        for sy in range((HEIGHT + STRUCTURE_SIZE - 1) // STRUCTURE_SIZE):
            width = min(STRUCTURE_SIZE, WIDTH - STRUCTURE_SIZE * sx)
            height = min(STRUCTURE_SIZE, HEIGHT - STRUCTURE_SIZE * sy)

            blocks = [
                Compound({
                    "pos": List[Int]([Int(4 * j), Int(0), Int(0)]),
                    "state": Int(0),
                    "nbt": Compound({
                        "id": String("minecraft:structure_block"),
                        "author": String("purplesyringa"),
                        "ignoreEntities": Byte(1),
                        "integrity": Float(1.0),
                        "metadata": String(""),
                        "mirror": String("NONE"),
                        "mode": String("LOAD"),
                        "name": String(f"badapple:frame{frame_num + 2 if frame_num < len(frames) else j}.{sx}{sy}v{VERSION}"),
                        "posX": Int(-4 * j),
                        "posY": Int(0),
                        "posZ": Int(0),
                        "powered": Byte(0),
                        "rotation": String("NONE"),
                        "seed": Long(0),
                        "showboundingbox": Byte(0),
                        "sizeX": Int(width),
                        "sizeY": Int(height),
                        "sizeZ": Int(DEPTH),
                        "showair": Byte(0)
                    })
                }),
                Compound({
                    "pos": List[Int]([2 * i + 4 * j, 0, 2 * (1 - i)]),
                    "state": Int(2)
                })
            ]
            palette = [
                Compound({
                    "Name": String("minecraft:structure_block"),
                    "Properties": Compound({
                        "mode": String("load")
                    })
                }),
                Compound({
                    "Name": String("minecraft:repeater"),
                    "Properties": Compound({
                        "delay": String("1"),
                        "facing": String(["east", "south"][i]),
                        "locked": String("false"),
                        "powered": String("false")
                    })
                }),
                Compound({
                    "Name": String("minecraft:air"),
                }),
                Compound({
                    "Name": String("minecraft:redstone_block"),
                }),
                Compound({
                    "Name": String("minecraft:stone"),
                })
            ]

            if frame_num < len(frames):
                blocks += [
                    Compound({
                        "pos": List[Int]([i + 4 * j, 0, 1 - i]),
                        "state": Int(2)
                    }),
                    Compound({
                        "pos": List[Int]([1 - i + 4 * j, 0, i]),
                        "state": Int(1)
                    }),
                    Compound({
                        "pos": List[Int]([2 * (1 - i) + 4 * j, 0, 2 * i]),
                        "state": Int(3)
                    })
                ]

                block_name_to_palette_index = {}

                for ix in range(width):
                    for iy in range(height):
                        x = sx * STRUCTURE_SIZE + ix
                        y = HEIGHT - 1 - (sy * STRUCTURE_SIZE + iy)

                        pixel = tuple(pix[x * 2 + dx, y * 2 + dy] for dx in range(2) for dy in range(2))
                        if pixel in common_super_pixels:
                            block_names = [common_blocks[common_super_pixels[pixel]], "barrier"]
                        else:
                            block_names = []
                            for z in range(2):
                                top = COLORS.index(pix[x * 2 + z, y * 2])
                                bottom = COLORS.index(pix[x * 2 + z, y * 2 + 1])
                                block_names.append(d_blocks[z][top + bottom * len(COLORS)])

                        for z, block_name in enumerate(block_names):
                            if last_frame[z][x][y] == block_name:
                                continue
                            last_frame[z][x][y] = block_name

                            if block_name not in block_name_to_palette_index:
                                block_name_to_palette_index[block_name] = len(palette)
                                palette.append(Compound({
                                    "Name": String(f"minecraft:{block_name}"),
                                }))
                            blocks.append(Compound({
                                "pos": List[Int]([ix, iy, 3 + z]),
                                "state": Int(block_name_to_palette_index[block_name])
                            }))
            else:
                if i == 0:
                    blocks += [
                        Compound({
                            "pos": List[Int]([i + 4 * j, 0, 1 - i]),
                            "state": Int(2)
                        })
                    ]
                blocks += [
                    Compound({
                        "pos": List[Int]([1 + 4 * j, 0, 0]),
                        "state": Int(4)
                    })
                ]

            File(Compound({
                "size": List[Int]([width, height, DEPTH]),
                "entities": List(),
                "blocks": List[Compound](blocks),
                "palette": List[Compound](palette),
                "DataVersion": Int(3955)
            })).save(f"{ROOT}/frame{frame_num}.{sx}{sy}v{VERSION}.nbt", gzipped=True)
