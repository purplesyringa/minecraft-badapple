import nbtlib
from nbtlib import File, Compound, List, Int, String, Byte, Long, Float
from PIL import Image
import os

ROOT = "/baka/minecraft/saves/Bad Apple!!/generated/minecraft/structures"
STRUCTURE_SIZE = 48
VERSION = 2
WIDTH = 64
HEIGHT = 48
DEPTH = 4

with open("/baka/minecraft/resourcepacks/Bad Apple!!/assets/simpleblocks") as f:
    simple_blocks = [name.strip() for name in f]

last_frame = [[-1] * HEIGHT for _ in range(WIDTH)]

for frame_num, frame in enumerate(sorted(os.listdir("frames"))):
    if frame_num % 10 == 0:
        print("Frame", frame_num)

    im = Image.open(f"frames/{frame}")
    pix = im.load()
    assert im.width == WIDTH * 2
    assert im.height == HEIGHT * 2

    i = frame_num // 2 % 2
    j = frame_num % 2

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
                        "name": String(f"minecraft:frame{frame_num + 2}.{sx}{sy}v{VERSION}"),
                        "posX": Int(-4 * j),
                        "posY": Int(0),
                        "posZ": Int(0),
                        "powered": Byte(0),
                        "rotation": String("NONE"),
                        "seed": Long(0),
                        "showboundingbox": Byte(1),
                        "sizeX": Int(width),
                        "sizeY": Int(height),
                        "sizeZ": Int(DEPTH),
                        "showair": Byte(0)
                    })
                }),
                Compound({
                    "pos": List[Int]([1 - i + 4 * j, 0, i]),
                    "state": Int(1)
                }),
                Compound({
                    "pos": List[Int]([i + 4 * j, 0, 1 - i]),
                    "state": Int(2)
                }),
                Compound({
                    "pos": List[Int]([2 * (1 - i) + 4 * j, 0, 2 * i]),
                    "state": Int(3)
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
                        "delay": Int(1),
                        "facing": String(["east", "south"][i]),
                        "locked": Byte(0),
                        "powered": Byte(0)
                    })
                }),
                Compound({
                    "Name": String("minecraft:air"),
                }),
                Compound({
                    "Name": String("minecraft:redstone_block"),
                })
            ]

            texture_id_to_palette_index = {}

            for ix in range(width):
                for iy in range(height):
                    x = sx * STRUCTURE_SIZE + ix
                    y = HEIGHT - 1 - (sy * STRUCTURE_SIZE + iy)
                    b1 = pix[x * 2, y * 2][0] // 0x4e
                    b2 = pix[x * 2, y * 2 + 1][0] // 0x4e
                    b3 = pix[x * 2 + 1, y * 2][0] // 0x4e
                    b4 = pix[x * 2 + 1, y * 2 + 1][0] // 0x4e
                    texture_id = (b1 << 6) | (b2 << 4) | (b3 << 2) | b4

                    if last_frame[x][y] == texture_id:
                        continue
                    last_frame[x][y] = texture_id

                    if texture_id not in texture_id_to_palette_index:
                        texture_id_to_palette_index[texture_id] = len(palette)
                        palette.append(Compound({
                            "Name": String(f"minecraft:{simple_blocks[texture_id]}"),
                        }))
                    blocks.append(Compound({
                        "pos": List[Int]([ix, iy, 3]),
                        "state": Int(texture_id_to_palette_index[texture_id])
                    }))

            File(Compound({
                "size": List[Int]([width, height, DEPTH]),
                "entities": List(),
                "blocks": List[Compound](blocks),
                "palette": List[Compound](palette),
                "DataVersion": Int(3955)
            })).save(f"{ROOT}/frame{frame_num}.{sx}{sy}v{VERSION}.nbt", gzipped=True)
