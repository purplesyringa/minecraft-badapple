mod types;

use crate::types::{Color, Config};
use image::RgbImage;
use std::cmp::Reverse;
use std::collections::HashMap;
use std::ffi::OsString;
use std::path::Path;

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

    let width_in_superpixels = config.video.width / config.superpixel.width;
    let height_in_superpixels = config.video.height / config.superpixel.height;

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir("../frames")
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    let mut statistics: HashMap<u128, usize> = HashMap::new();

    let mut last_frame_values = vec![vec![0; width_in_superpixels]; height_in_superpixels];

    for (frame_num, frame_file_name) in frame_file_names.iter().enumerate() {
        if frame_num % 10 == 0 {
            eprintln!("Frame {frame_num}");
        }

        let frame_path = Path::new("../frames").join(frame_file_name);
        let frame = image::open(frame_path).expect("Invalid frame");
        assert_eq!(frame.width() as usize, config.video.width);
        assert_eq!(frame.height() as usize, config.video.height);
        let frame: RgbImage = frame.into_rgb8();

        let mut values_to_increment = Vec::new();

        for superpixel_y in 0..height_in_superpixels {
            for superpixel_x in 0..width_in_superpixels {
                let mut value = 0u128;
                for y in 0..config.superpixel.height {
                    for x in 0..config.superpixel.width {
                        let subpixel_x = superpixel_x * config.superpixel.width + x;
                        let subpixel_y =
                            config.video.height - (superpixel_y + 1) * config.superpixel.height + y;
                        let pixel = frame.get_pixel(subpixel_x as u32, subpixel_y as u32);
                        let color = Color(pixel.0[0], pixel.0[1], pixel.0[2]);
                        value = value * config.colors.len() as u128 + color_to_id[&color] as u128;
                    }
                }

                let prev_value =
                    std::mem::replace(&mut last_frame_values[superpixel_y][superpixel_x], value);
                if prev_value != value {
                    values_to_increment.push(prev_value);
                    values_to_increment.push(value);
                }
            }
        }

        let coeff = values_to_increment.len();
        for value in values_to_increment {
            *statistics.entry(value).or_default() += coeff;
        }
    }

    let mut statistics: Vec<(u128, usize)> = statistics.into_iter().collect();
    statistics.sort_by_key(|stat| Reverse(stat.1));

    let predictions: Vec<u128> = statistics[..8192].iter().map(|(value, _)| *value).collect();

    std::fs::write(
        "../superpixel_predictions.json",
        serde_json::to_string(&predictions).expect("Failed to serialize predictions"),
    )
    .expect("Failed to write predictions");
}
