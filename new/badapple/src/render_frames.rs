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

#[derive(Deserialize)]
struct RenderRules {
    pixel: Vec<EquivalentBlockStates>,
    superpixel: Vec<EquivalentBlockStates>,
}

#[derive(Serialize)]
struct Coordinates(i32, i32, i32);

#[derive(Serialize)]
struct BlockInfo {
    pos: Coordinates,
    state: i16,
    nbt: Option<Value>,
}

#[derive(Serialize)]
struct PaletteEntry<'a> {
    #[serde(rename = "Name")]
    name: &'a str,
    #[serde(rename = "Properties")]
    properties: Option<NBT>,
}

#[derive(Serialize)]
struct Structure<'a> {
    size: Coordinates,
    entities: Vec<()>,
    blocks: Vec<BlockInfo>,
    palette: Vec<PaletteEntry<'a>>,
    #[serde(rename = "DataVersion")]
    data_version: i32,
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
enum TextureId {
    Unknown,
    Barrier,
    Pixel(usize),
    Superpixel(usize),
}

const STRUCTURE_SIZE: usize = 48;
const VERSION: usize = 2;
const DEPTH: usize = 7;

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let color_to_id: HashMap<Color, usize> = config
        .colors
        .iter()
        .enumerate()
        .map(|(i, color)| (*color, i))
        .collect();

    let superpixel_predictions: Vec<u128> = serde_json::from_str(
        &std::fs::read_to_string("../superpixel_predictions.json")
            .expect("Failed to read superpixel_predictions.json"),
    )
    .expect("Invalid superpixel predictions");
    let superpixel_predictions: HashMap<u128, usize> = superpixel_predictions
        .into_iter()
        .enumerate()
        .map(|(i, value)| (value, i))
        .collect();

    let width_in_blocks = config.video.width / config.pixel.width;
    let height_in_blocks = config.video.height / config.pixel.height;
    let pixels_in_superpixel_width = config.superpixel.width / config.pixel.width;
    let pixels_in_superpixel_height = config.superpixel.height / config.pixel.height;
    let pixels_in_superpixel = pixels_in_superpixel_width * pixels_in_superpixel_height;

    let barrier_blockstates = [BlockState {
        block: "barrier".to_string(),
        state: NBT(HashMap::new()),
    }];

    let render_rules: RenderRules = serde_json::from_str(
        &std::fs::read_to_string("../render_rules.json").expect("Failed to read render_rules.json"),
    )
    .expect("Invalid render rules");

    let mut current_video_textures: Vec<Vec<TextureId>> =
        vec![vec![TextureId::Unknown; width_in_blocks]; height_in_blocks];

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir(&config.frames_root)
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    let superpixel_texture_x = [0, 0, 1][pixels_in_superpixel_width - 1];
    let superpixel_texture_y = [0, 1, 1][pixels_in_superpixel_height - 1];
    let superpixel_texture_offset =
        superpixel_texture_y * pixels_in_superpixel_width + superpixel_texture_x;

    for frame_num in 0..frame_file_names.len() + 2 {
        if frame_num % 10 == 0 {
            eprintln!("Frame {frame_num}");
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

        for megapixel_x in 0..width_in_blocks.div_ceil(STRUCTURE_SIZE) {
            for megapixel_y in 0..height_in_blocks.div_ceil(STRUCTURE_SIZE) {
                let structure_width_in_blocks =
                    STRUCTURE_SIZE.min(width_in_blocks - STRUCTURE_SIZE * megapixel_x);
                let structure_height_in_blocks =
                    STRUCTURE_SIZE.min(height_in_blocks - STRUCTURE_SIZE * megapixel_y);

                let structure_width_in_superpixels = (structure_width_in_blocks
                    * config.pixel.width)
                    .div_ceil(config.superpixel.width);
                let structure_height_in_superpixels = (structure_height_in_blocks
                    * config.pixel.height)
                    .div_ceil(config.superpixel.height);

                let mut blocks = vec![BlockInfo {
                    pos: Coordinates(4 * parity as i32, 0, 0),
                    state: 0,
                    nbt: Some(nbt!({
                        "id": "structure_block",
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
                        "sizeX": structure_width_in_blocks as i32,
                        "sizeY": structure_height_in_blocks as i32,
                        "sizeZ": DEPTH as i32,
                        "showair": 0i8,
                    })),
                }];

                let mut palette = vec![
                    PaletteEntry {
                        name: "structure_block",
                        properties: Some(NBT([("mode".to_string(), "load".to_string())].into())),
                    },
                    PaletteEntry {
                        name: "repeater",
                        properties: Some(NBT([
                            ("delay", "1"),
                            ("facing", ["east", "south"][half_parity]),
                            ("locked", "false"),
                            ("powered", "false"),
                        ]
                        .map(|(key, value)| (key.into(), value.into()))
                        .into())),
                    },
                    PaletteEntry {
                        name: "air",
                        properties: None,
                    },
                    PaletteEntry {
                        name: "stone",
                        properties: None,
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

                    for superpixel_y in 0..structure_height_in_superpixels {
                        for superpixel_x in 0..structure_width_in_superpixels {
                            let superpixel_x0 = megapixel_x * STRUCTURE_SIZE * config.pixel.width
                                + superpixel_x * config.superpixel.width;
                            let superpixel_y0 = config.video.height.wrapping_sub(
                                megapixel_y * STRUCTURE_SIZE * config.pixel.height
                                    + (superpixel_y + 1) * config.superpixel.height,
                            );

                            let mut superpixel_value: u128 = 0;
                            let mut subpixel_values: Vec<usize> = vec![0; pixels_in_superpixel];

                            for dy in 0..config.superpixel.height {
                                for dx in 0..config.superpixel.width {
                                    let x = superpixel_x0 + dx;
                                    let y = superpixel_y0.wrapping_add(dy);

                                    if x >= config.video.width || (y as isize) < 0 {
                                        continue;
                                    }

                                    let pixel = frame.get_pixel(x as u32, y as u32);
                                    let color = Color(pixel.0[0], pixel.0[1], pixel.0[2]);
                                    let color_id = color_to_id[&color];

                                    superpixel_value = superpixel_value
                                        * config.colors.len() as u128
                                        + color_id as u128;

                                    let subpixel_id =
                                        (dy / config.pixel.height * config.superpixel.width + dx)
                                            / config.pixel.width;
                                    subpixel_values[subpixel_id] = subpixel_values[subpixel_id]
                                        * config.colors.len()
                                        + color_id;
                                }
                            }

                            let mut textures: Vec<TextureId> =
                                subpixel_values.into_iter().map(TextureId::Pixel).collect();

                            if superpixel_x0 + config.superpixel.width <= config.video.width
                                && ((superpixel_y0 + config.superpixel.height) as isize) > 0
                            {
                                if let Some(superpixel_texture_id) =
                                    superpixel_predictions.get(&superpixel_value)
                                {
                                    textures = vec![TextureId::Barrier; pixels_in_superpixel];
                                    textures[superpixel_texture_offset] =
                                        TextureId::Superpixel(*superpixel_texture_id);
                                }
                            }

                            for (i, texture_id) in textures.into_iter().enumerate() {
                                let dy = i / pixels_in_superpixel_width;
                                let dx = i % pixels_in_superpixel_width;

                                let relative_block_x =
                                    superpixel_x * pixels_in_superpixel_width + dx;
                                let relative_block_y = superpixel_y * pixels_in_superpixel_height
                                    + pixels_in_superpixel_height
                                    - 1
                                    - dy;

                                let block_x = megapixel_x * STRUCTURE_SIZE + relative_block_x;
                                let block_y = megapixel_y * STRUCTURE_SIZE + relative_block_y;

                                if block_x >= width_in_blocks || block_y >= height_in_blocks {
                                    continue;
                                }

                                if std::mem::replace(
                                    &mut current_video_textures[block_y][block_x],
                                    texture_id,
                                ) == texture_id
                                {
                                    continue;
                                }

                                let render_rule_blockstates: &[BlockState] = match texture_id {
                                    TextureId::Unknown => unreachable!(),
                                    TextureId::Barrier => &barrier_blockstates,
                                    TextureId::Pixel(id) => &render_rules.pixel[id],
                                    TextureId::Superpixel(id) => &render_rules.superpixel[id],
                                };
                                let blockstate_index =
                                    (block_x + block_y) % render_rule_blockstates.len();
                                let blockstate = &render_rule_blockstates[blockstate_index];

                                let state = blockstate_palette_index
                                    .entry((texture_id, blockstate_index))
                                    .or_insert_with(|| {
                                        palette.push(PaletteEntry {
                                            name: &blockstate.block,
                                            properties: if blockstate.state.0.is_empty() {
                                                None
                                            } else {
                                                Some(blockstate.state.clone())
                                            },
                                        });
                                        palette.len() - 1
                                    });

                                blocks.push(BlockInfo {
                                    pos: Coordinates(
                                        relative_block_x as i32,
                                        relative_block_y as i32,
                                        3,
                                    ),
                                    state: (*state).try_into().expect("too many states"),
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
                    size: Coordinates(
                        structure_width_in_blocks as i32,
                        structure_height_in_blocks as i32,
                        DEPTH as i32,
                    ),
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
