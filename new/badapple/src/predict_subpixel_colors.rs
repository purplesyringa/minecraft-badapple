mod types;

use crate::types::{Color, Config, Prediction};
use image::RgbImage;
use itertools::Itertools;
use std::cmp::Reverse;
use std::collections::{hash_map::Entry, HashMap, HashSet};
use std::ffi::OsString;

type PixelStat = HashMap<Color, usize>;

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let block_width = config.video.width / config.subpixels.width;
    let block_height = config.video.height / config.subpixels.height;
    let n_subpixels = config.subpixels.width * config.subpixels.height;

    let mut subpixels_by_z = vec![Vec::new(); 4];
    for (y, row) in config.subpixels.distribution.iter().enumerate() {
        for (x, z) in row.iter().enumerate() {
            subpixels_by_z[*z].push((x, y));
        }
    }

    let mut frame_file_names: Vec<OsString> = std::fs::read_dir(&config.frames_root)
        .expect("Cannot read frames directory")
        .map(|file| file.expect("Cannot read frames directory").file_name())
        .collect();
    frame_file_names.sort();

    let mut pixel_statistics: HashMap<Vec<Color>, usize> = HashMap::new();
    let mut z0_prediction_groups: HashMap<Vec<Color>, Vec<PixelStat>> = HashMap::new();

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

                *pixel_statistics.entry(value.clone()).or_default() += 1;

                let stat = z0_prediction_groups
                    .entry(key)
                    .or_insert_with(|| vec![HashMap::new(); n_subpixels]);
                for (subpixel_index, color) in value.into_iter().enumerate() {
                    *stat[subpixel_index].entry(color).or_default() += 1;
                }
            }
        }
    }

    let mut predictions: [HashMap<Vec<Color>, Vec<Color>>; 3] =
        std::array::from_fn(|_| HashMap::new());
    let mut predicted_pixels: HashSet<Vec<Color>> = HashSet::new();

    // For z = 0, predict each subpixel individually
    for (key, stat_by_subpixel) in z0_prediction_groups {
        let value: Vec<Color> = stat_by_subpixel
            .into_iter()
            .map(|stat| stat.into_iter().max_by_key(|(_, count)| *count).unwrap().0)
            .collect();

        predictions[0].insert(key, value.clone());
        predicted_pixels.insert(value);
    }

    // For z = 1, 2, predict the whole pixel
    let mut pixel_statistics: Vec<(Vec<Color>, usize)> = pixel_statistics.into_iter().collect();
    pixel_statistics.sort_by_key(|stat| Reverse(stat.1));

    // Fully assign each z in order to minimize z changes
    for z in 1..3 {
        let max_total_predictions = config.colors.len().pow(subpixels_by_z[z].len() as u32);

        for (value, _) in &pixel_statistics {
            if predictions[z].len() == max_total_predictions {
                break;
            }
            if predicted_pixels.contains(value) {
                continue;
            }

            let key: Vec<Color> = (0..config.subpixels.height)
                .cartesian_product(0..config.subpixels.width)
                .zip(value)
                .filter(|&((y, x), _)| config.subpixels.distribution[y][x] == z)
                .map(|(_, color)| *color)
                .collect();

            if let Entry::Vacant(entry) = predictions[z].entry(key) {
                entry.insert(value.clone());
                predicted_pixels.insert(value.clone());
            }
        }
    }

    eprintln!("Unpredicted pixels:");
    for (value, count) in pixel_statistics
        .into_iter()
        .filter(|(value, _)| !predicted_pixels.contains(value))
        .take(256)
    {
        eprintln!("{count}: {value:?}");
    }

    let predictions: [Vec<Prediction>; 3] = predictions.map(|z_predictions| {
        z_predictions
            .into_iter()
            .map(|(from, to)| Prediction { from, to })
            .collect()
    });

    println!(
        "{}",
        serde_json::to_string(&predictions).expect("Failed to serialize predictions")
    );
}
