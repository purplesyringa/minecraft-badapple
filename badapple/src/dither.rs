mod types;

use crate::types::Config;
use image::GrayImage;
use std::path::Path;

fn main() {
    let config: Config = serde_json::from_str(
        &std::fs::read_to_string("../config.json").expect("Failed to read config.json"),
    )
    .expect("Invalid config");

    let mut palette: Vec<u8> = config
        .colors
        .iter()
        .map(|color| {
            assert!(
                color.0 == color.1 && color.1 == color.2,
                "Only gray-scale dithering is supported"
            );
            color.0
        })
        .collect();
    palette.sort();

    let inv_gamma = 1.0 / config.gamma;
    let (min, max) = config.in_color_range;

    let noise = image::open("../bluenoise.png")
        .expect("Invalid blue noise")
        .into_luma8();

    for file_entry in std::fs::read_dir("../origframes").expect("read origframes") {
        let file_entry = file_entry.expect("read origframes");

        let in_frame = image::open(file_entry.path())
            .expect("Invalid frame")
            .into_luma8();

        let mut out_frame = GrayImage::new(in_frame.width(), in_frame.height());

        for ((in_pixel, out_pixel), noise_pixel) in in_frame
            .pixels()
            .zip(out_frame.pixels_mut())
            .zip(noise.pixels())
        {
            let value: u8 = (in_pixel.0[0].saturating_sub(min) as u16 * 255 / (max - min) as u16)
                .try_into()
                .unwrap_or(255);
            let noise = noise_pixel.0[0];

            let i = palette.partition_point(|&x| x < value);
            let dithered_value = if value == palette[i] {
                value
            } else {
                let low = palette[i - 1];
                let high = palette[i];
                let take_high = (noise as f32)
                    < 256.0 * ((value - low) as f32 / (high - low) as f32).powf(inv_gamma);
                if take_high {
                    high
                } else {
                    low
                }
            };

            out_pixel.0[0] = dithered_value;
        }

        out_frame
            .save(Path::new("../frames").join(file_entry.file_name()))
            .expect("Failed to write output frame");
    }
}
