mod types;

use crate::types::{Color, Config};
use fastnbt::{nbt, value::Value};
use flate2::{write::GzEncoder, Compression};
use image::RgbImage;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::ffi::OsString;
use std::fs::File;
use std::io::{BufWriter, Write};

#[derive(Serialize, Deserialize, PartialEq, Clone)]
struct NBT(HashMap<String, String>);

#[derive(Deserialize, PartialEq, Clone)]
struct BlockState {
    block: String,
    state: NBT,
}

type EquivalentBlockStates = Vec<BlockState>;

#[derive(Deserialize, PartialEq, Eq, Hash)]
struct RenderRuleKey {
    z: usize,
    subpixel_colors: Vec<Color>,
}

#[derive(Deserialize)]
struct RenderRule {
    #[serde(flatten)]
    key: RenderRuleKey,
    blockstates: EquivalentBlockStates,
}

struct ParsedRenderRule {
    id: usize,
    blockstates: EquivalentBlockStates,
}

#[derive(Serialize)]
struct Coordinates(i32, i32, i32);

#[derive(Serialize)]
struct BlockInfo {
    pos: Coordinates,
    state: i32,
    nbt: Option<Value>,
}

#[derive(Serialize)]
struct PaletteEntry {
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "Properties")]
    properties: NBT,
}

#[derive(Serialize)]
struct Structure {
    size: Coordinates,
    entities: Vec<()>,
    blocks: Vec<BlockInfo>,
    palette: Vec<PaletteEntry>,
    #[serde(rename = "DataVersion")]
    data_version: i32,
}

const STRUCTURE_SIZE: usize = 48;
const VERSION: usize = 2;
const DEPTH: usize = 7;

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let block_width = config.video.width / config.subpixels.width;
    let block_height = config.video.height / config.subpixels.height;

    let mut subpixels_by_z = vec![Vec::new(); 4];
    for (y, row) in config.subpixels.distribution.iter().enumerate() {
        for (x, z) in row.iter().enumerate() {
            subpixels_by_z[*z].push((x, y));
        }
    }

    let mut render_rules = HashMap::new();
    for render_rule in serde_json::from_str::<Vec<RenderRule>>(
        &std::fs::read_to_string("../render_rules.json").expect("Failed to read render_rules.json"),
    )
    .expect("Invalid render rules")
    {
        render_rules.insert(
            render_rule.key,
            ParsedRenderRule {
                id: render_rules.len(),
                blockstates: render_rule.blockstates,
            },
        );
    }

    let mut current_video_blockstates: Vec<Vec<[(usize, usize); 4]>> = (0..block_width)
        .map(|_x| {
            (0..block_height)
                .map(|_y| [(usize::MAX, usize::MAX); 4])
                .collect()
        })
        .collect();

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir(&config.frames_root)
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    for frame_num in 0..frame_file_names.len() + 2 {
        if frame_num % 10 == 0 {
            println!("Frame {frame_num}");
        }

        let half_parity = frame_num / 2 % 2;
        let parity = frame_num % 2;

        let frame: Option<RgbImage> = frame_file_names.get(frame_num).map(|frame_file_name| {
            let frame_path = config.frames_root.join(frame_file_name);
            let frame = image::open(frame_path).expect("Invalid frame");
            assert_eq!(frame.width() as usize, config.video.width);
            assert_eq!(frame.height() as usize, config.video.height);
            frame.to_rgb8()
        });

        for megapixel_x in 0..block_width.div_ceil(STRUCTURE_SIZE) {
            for megapixel_y in 0..block_height.div_ceil(STRUCTURE_SIZE) {
                let width = STRUCTURE_SIZE.min(block_width - STRUCTURE_SIZE * megapixel_x);
                let height = STRUCTURE_SIZE.min(block_height - STRUCTURE_SIZE * megapixel_y);

                let mut blocks = vec![BlockInfo {
                    pos: Coordinates(4 * parity as i32, 0, 0),
                    state: 0,
                    nbt: Some(nbt!({
                        "id": "minecraft:structure_block",
                        "author": "purplesyringa",
                        "ignoreEntities": 1i8,
                        "integrity": 1.0f32,
                        "metadata": "",
                        "mirror": "NONE",
                        "mode": "LOAD",
                        "name": format!(
                            "badapple:frame{}.{megapixel_x}{megapixel_y}v{VERSION}",
                            if frame_num < frame_file_names.len() {
                                frame_num + 2
                            } else {
                                parity
                            },
                        ),
                        "posX": -4 * parity as i32,
                        "posY": 0i32,
                        "posZ": 0i32,
                        "powered": 0i8,
                        "rotation": "NONE",
                        "seed": 0i64,
                        "showboundingbox": 0i8,
                        "sizeX": width as i32,
                        "sizeY": height as i32,
                        "sizeZ": DEPTH as i32,
                        "showair": 0i8,
                    })),
                }];

                let mut palette = vec![
                    PaletteEntry {
                        name: "minecraft:structure_block".to_string(),
                        properties: NBT([("mode".to_string(), "load".to_string())].into()),
                    },
                    PaletteEntry {
                        name: "minecraft:repeater".to_string(),
                        properties: NBT([
                            ("delay", "1"),
                            ("facing", ["east", "south"][half_parity]),
                            ("locked", "false"),
                            ("powered", "false"),
                        ]
                        .map(|(key, value)| (key.into(), value.into()))
                        .into()),
                    },
                    PaletteEntry {
                        name: "minecraft:air".to_string(),
                        properties: NBT(HashMap::new()),
                    },
                    PaletteEntry {
                        name: "minecraft:stone".to_string(),
                        properties: NBT(HashMap::new()),
                    },
                ];

                if let Some(ref frame) = frame {
                    blocks.push(BlockInfo {
                        pos: Coordinates(
                            (half_parity + 4 * parity) as i32,
                            0,
                            1 - half_parity as i32,
                        ),
                        state: 2,
                        nbt: None,
                    });
                    blocks.push(BlockInfo {
                        pos: Coordinates(
                            (1 - half_parity + 4 * parity) as i32,
                            0,
                            half_parity as i32,
                        ),
                        state: 1,
                        nbt: None,
                    });

                    let mut blockstate_palette_index = HashMap::new();

                    for relative_x in 0..width {
                        for relative_y in 0..height {
                            let block_x = megapixel_x * STRUCTURE_SIZE + relative_x;
                            let block_y =
                                block_height - 1 - (megapixel_y * STRUCTURE_SIZE + relative_y);

                            for z in 0..4 {
                                let subpixel_colors: Vec<Color> = subpixels_by_z[z]
                                    .iter()
                                    .map(|(relative_subpixel_x, relative_subpixel_y)| {
                                        let subpixel_x =
                                            block_x * config.subpixels.width + relative_subpixel_x;
                                        let subpixel_y =
                                            block_y * config.subpixels.height + relative_subpixel_y;
                                        let pixel =
                                            frame.get_pixel(subpixel_x as u32, subpixel_y as u32);
                                        Color(pixel.0[0], pixel.0[1], pixel.0[2])
                                    })
                                    .collect();

                                let render_rule = &render_rules[&RenderRuleKey {
                                    z,
                                    subpixel_colors: subpixel_colors.clone(),
                                }];
                                let index = (block_x + block_y + z) % render_rule.blockstates.len();
                                let blockstate = &render_rule.blockstates[index];

                                let cur = &mut current_video_blockstates[block_x][block_y][z];
                                if *cur == (render_rule.id, index) {
                                    continue;
                                }
                                *cur = (render_rule.id, index);

                                let blockstate_key = (z, subpixel_colors, index);

                                let state = blockstate_palette_index
                                    .entry(blockstate_key)
                                    .or_insert_with(|| {
                                        palette.push(PaletteEntry {
                                            name: format!("minecraft:{}", blockstate.block),
                                            properties: blockstate.state.clone(),
                                        });
                                        palette.len() - 1
                                    });

                                blocks.push(BlockInfo {
                                    pos: Coordinates(
                                        relative_x as i32,
                                        relative_y as i32,
                                        3 + z as i32,
                                    ),
                                    state: *state as i32,
                                    nbt: None,
                                });
                            }
                        }
                    }
                } else {
                    if half_parity == 0 {
                        blocks.push(BlockInfo {
                            pos: Coordinates(
                                (half_parity + 4 * parity) as i32,
                                0,
                                1 - half_parity as i32,
                            ),
                            state: 2,
                            nbt: None,
                        });
                    }
                    blocks.push(BlockInfo {
                        pos: Coordinates(1 + 4 * parity as i32, 0, 0),
                        state: 3,
                        nbt: None,
                    });
                }

                let structure = Structure {
                    size: Coordinates(width as i32, height as i32, DEPTH as i32),
                    entities: Vec::new(),
                    blocks,
                    palette,
                    data_version: 3955,
                };

                let file = File::create(format!(
                    "{}/frame{frame_num}.{megapixel_x}{megapixel_y}v{VERSION}.nbt",
                    config.structures_root
                ))
                .expect("Cannot create NBT file");
                let mut encoder = GzEncoder::new(BufWriter::new(file), Compression::default());
                encoder
                    .write_all(&fastnbt::to_bytes(&structure).expect("Failed to serialize NBT"))
                    .expect("Failed to write NBT");
                encoder.finish().expect("Failed to write NBT");
            }
        }
    }
}
