mod types;

use crate::types::{Color, Config};
use image::RgbImage;
use serde::Serialize;
use std::collections::HashMap;
use std::ffi::OsString;

#[derive(Serialize)]
struct Prediction {
    from: Vec<Color>,
    to: Vec<Color>,
}

type PixelStat = HashMap<Color, usize>;

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let block_width = config.video.width / config.subpixels.width;
    let block_height = config.video.height / config.subpixels.height;
    let n_subpixels = config.subpixels.width * config.subpixels.height;

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir(&config.frames_root)
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    let mut prediction_groups: HashMap<Vec<Color>, Vec<PixelStat>> = HashMap::new();

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
                // Predict all colors based on colors of the z = 0 slice
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

                let stat = prediction_groups
                    .entry(key)
                    .or_insert_with(|| vec![HashMap::new(); n_subpixels]);
                for (subpixel_index, color) in value.into_iter().enumerate() {
                    *stat[subpixel_index].entry(color).or_default() += 1;
                }
            }
        }
    }

    let predictions: Vec<Prediction> = prediction_groups
        .into_iter()
        .map(|(key, stat_by_subpixel)| {
            let most_common_color_by_subpixel: Vec<Color> = stat_by_subpixel
                .into_iter()
                .map(|stat| stat.into_iter().max_by_key(|(_, count)| *count).unwrap().0)
                .collect();

            Prediction {
                from: key,
                to: most_common_color_by_subpixel,
            }
        })
        .collect();

    println!(
        "{}",
        serde_json::to_string(&predictions).expect("Failed to serialize predictions")
    );
}
