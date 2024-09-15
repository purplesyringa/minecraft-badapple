import nbtlib
from nbtlib import File, Compound, List, Int, String, Byte, Long, Float

ROOT = "/baka/minecraft/saves/Bad Apple!!/generated/badapple/structures"
VERSION = 1

File(Compound({
    "size": List[Int]([1, 48, 48]),
    "entities": List(),
    "blocks": List[Compound]([
        Compound({
            "pos": List[Int]([0, 0, 0]),
            "state": Int(0)
        }),
        Compound({
            "pos": List[Int]([0, 47, 0]),
            "state": Int(0)
        }),
        Compound({
            "pos": List[Int]([0, 25, 47]),
            "state": Int(1)
        }),
        Compound({
            "pos": List[Int]([0, 26, 47]),
            "state": Int(1)
        })
    ]),
    "palette": List[Compound]([
        Compound({
            "Name": String("minecraft:redstone_torch")
        }),
        Compound({
            "Name": String("minecraft:air")
        })
    ]),
    "DataVersion": Int(3955)
})).save(f"{ROOT}/headv{VERSION}.nbt", gzipped=True)

File(Compound({
    "size": List[Int]([1, 2, 1]),
    "entities": List(),
    "blocks": List[Compound]([
        Compound({
            "pos": List[Int]([0, 0, 0]),
            "state": Int(0)
        }),
        Compound({
            "pos": List[Int]([0, 1, 0]),
            "state": Int(1),
            "nbt": Compound({
                "id": String("minecraft:structure_block"),
                "author": String("purplesyringa"),
                "ignoreEntities": Byte(1),
                "integrity": Float(1.0),
                "metadata": String(""),
                "mirror": String("NONE"),
                "mode": String("LOAD"),
                "name": String(f"badapple:headv{VERSION}"),
                "posX": Int(0),
                "posY": Int(-26),
                "posZ": Int(-47),
                "powered": Byte(0),
                "rotation": String("NONE"),
                "seed": Long(0),
                "showboundingbox": Byte(0),
                "sizeX": Int(1),
                "sizeY": Int(48),
                "sizeZ": Int(48),
                "showair": Byte(0)
            })
        })
    ]),
    "palette": List[Compound]([
        Compound({
            "Name": String("minecraft:redstone_block")
        }),
        Compound({
            "Name": String("minecraft:structure_block"),
            "Properties": Compound({
                "mode": String("load")
            })
        })
    ]),
    "DataVersion": Int(3955)
})).save(f"{ROOT}/starterv{VERSION}.nbt", gzipped=True)
