mod types;

use crate::types::{Color, Config, Prediction};
use image::RgbImage;
use itertools::Itertools;
use serde::Serialize;
use std::collections::HashMap;
use std::ffi::OsString;

#[derive(Serialize)]
struct UnpredictablePixel {
    colors: Vec<Color>,
    count: usize,
}

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let block_width = config.video.width / config.subpixels.width;
    let block_height = config.video.height / config.subpixels.height;

    let subpixel_predictions: HashMap<Vec<Color>, Vec<Color>> =
        serde_json::from_str::<Vec<Prediction>>(
            &std::fs::read_to_string("../subpixel_predictions.json")
                .expect("Failed to read subpixel_predictions.json"),
        )
        .expect("Invalid subpixel predictions")
        .into_iter()
        .map(|prediction| (prediction.from, prediction.to))
        .collect();

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir(&config.frames_root)
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    let mut unpredictable_pixels: HashMap<Vec<Color>, usize> = HashMap::new();

    for (frame_num, frame_file_name) in frame_file_names.iter().enumerate() {
        if frame_num % 10 == 0 {
            eprintln!("Frame {frame_num}");
        }

        let frame_path = config.frames_root.join(frame_file_name);
        let frame = image::open(frame_path).expect("Invalid frame");
        assert_eq!(frame.width() as usize, config.video.width);
        assert_eq!(frame.height() as usize, config.video.height);
        let frame: RgbImage = frame.to_rgb8();

        for block_x in 0..block_width {
            for block_y in 0..block_height {
                // Check if all colors can be predicted from the z = 0 slice
                let mut key = Vec::new();
                let mut value = Vec::new();

                for relative_subpixel_y in 0..config.subpixels.height {
                    for relative_subpixel_x in 0..config.subpixels.width {
                        let z =
                            config.subpixels.distribution[relative_subpixel_y][relative_subpixel_x];

                        let subpixel_x = block_x * config.subpixels.width + relative_subpixel_x;
                        let subpixel_y = block_y * config.subpixels.height + relative_subpixel_y;
                        let pixel = frame.get_pixel(subpixel_x as u32, subpixel_y as u32);
                        let color = Color(pixel.0[0], pixel.0[1], pixel.0[2]);

                        if z == 0 {
                            key.push(color);
                        }
                        value.push(color);
                    }
                }

                if subpixel_predictions.get(&key) == Some(&value) {
                    continue;
                }

                *unpredictable_pixels.entry(value).or_insert(0) += 1;
            }
        }
    }

    let common_pixels: Vec<UnpredictablePixel> = unpredictable_pixels
        .into_iter()
        .map(|(colors, count)| UnpredictablePixel { colors, count })
        .k_largest_by_key(16384, |pixel| pixel.count)
        .collect();

    println!(
        "{}",
        serde_json::to_string(&common_pixels).expect("Failed to serialize common pixels")
    );
}
