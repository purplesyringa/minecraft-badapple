import nbtlib
from nbtlib import File, Compound, List, Int, String, Byte, Long, Float

ROOT = "/baka/minecraft/saves/Bad Apple!!/generated/badapple/structures"
VERSION = 2


def structure(name: str, size: tuple[int, int, int], *blocks: tuple[Compound, ...]):
    File(Compound({
        "size": List[Int](size),
        "entities": List(),
        "blocks": List[Compound](blocks),
        "palette": List[Compound]([
            Compound({
                "Name": String("minecraft:redstone_block")
            }),
            Compound({
                "Name": String("minecraft:structure_block"),
                "Properties": Compound({
                    "mode": String("load")
                })
            }),
            Compound({
                "Name": String("minecraft:air")
            }),
            Compound({
                "Name": String("minecraft:redstone_torch")
            })
        ]),
        "DataVersion": Int(3955)
    })).save(f"{ROOT}/{name}v{VERSION}.nbt", gzipped=True)


def redstone_block(pos: tuple[int, int, int]) -> Compound:
    return Compound({
        "pos": List[Int](pos),
        "state": Int(0)
    })


def structure_block(pos: tuple[int, int, int], offset: tuple[int, int, int], size: tuple[int, int, int], name: str) -> Compound:
    return Compound({
        "pos": List[Int](pos),
        "state": Int(1),
        "nbt": Compound({
            "id": String("minecraft:structure_block"),
            "author": String("purplesyringa"),
            "ignoreEntities": Byte(1),
            "integrity": Float(1.0),
            "metadata": String(""),
            "mirror": String("NONE"),
            "mode": String("LOAD"),
            "name": String(f"badapple:{name}v{VERSION}"),
            "posX": Int(offset[0]),
            "posY": Int(offset[1]),
            "posZ": Int(offset[2]),
            "powered": Byte(0),
            "rotation": String("NONE"),
            "seed": Long(0),
            "showboundingbox": Byte(0),
            "sizeX": Int(size[0]),
            "sizeY": Int(size[1]),
            "sizeZ": Int(size[2]),
            "showair": Byte(0)
        })
    })


def air(pos: tuple[int, int, int]) -> Compound:
    return Compound({
        "pos": List[Int](pos),
        "state": Int(2)
    })


def redstone_torch(pos: tuple[int, int, int]) -> Compound:
    return Compound({
        "pos": List[Int](pos),
        "state": Int(3)
    })


structure(
    "starter1",
    (48, 2, 1),
    redstone_block((47, 0, 0)),
    structure_block((47, 1, 0), offset=(0, -1, -47), size=(22, 2, 48), name="starter2")
)

structure(
    "starter2",
    (22, 2, 48),
    air((0, 0, 47)),
    air((0, 1, 47)),
    redstone_block((21, 0, 0)),
    structure_block((21, 1, 0), offset=(0, -1, -47), size=(1, 2, 48), name="starter3")
)

structure(
    "starter3",
    (1, 2, 48),
    air((0, 0, 47)),
    air((0, 1, 47)),
    redstone_block((0, 0, 0)),
    structure_block((0, 1, 0), offset=(0, -1, -22), size=(1, 2, 23), name="starter4")
)

structure(
    "starter4",
    (1, 2, 23),
    air((0, 0, 22)),
    air((0, 1, 22)),
    redstone_torch((0, 0, 0))
)
