use itertools::Itertools;
use std::fs::File;
use std::io::BufWriter;
use std::path::PathBuf;

const WIDTH: usize = 512;
const HEIGHT: usize = 384;
const GAMMA: f64 = 1.0;
const HALFTONES: u16 = 4;

fn build_table(power: f64, inmin: u8, inmax: u8) -> [u8; 256] {
    (0..=255)
        .map(|x: u8| {
            ((x.saturating_sub(inmin) as f64 / (inmax - inmin) as f64).powf(power) * 255.0).round()
                as u8
        })
        .collect::<Vec<u8>>()
        .try_into()
        .unwrap()
}

fn main() {
    let from_linear = build_table(GAMMA, 0, 255);
    let to_linear = build_table(1.0 / GAMMA, 16, 239);

    let palette: Vec<u8> = (0..HALFTONES)
        .map(|x| from_linear[(x * 255 / (HALFTONES - 1)) as usize])
        .collect();
    println!("Palette: {:?}", palette);

    let frame = File::open("../bluenoise.png").expect("open noise");
    let decoder = png::Decoder::new(frame);
    let mut reader = decoder.read_info().expect("read PNG");
    let mut buf = vec![0; reader.output_buffer_size()];
    let info = reader.next_frame(&mut buf).expect("read PNG");
    let noise_bytes = &buf[..info.buffer_size()];

    for file_entry in std::fs::read_dir("../origframes").expect("read origframes") {
        let file_entry = file_entry.expect("read origframes");

        let frame = File::open(file_entry.path()).expect("open original frame");
        let decoder = png::Decoder::new(frame);
        let mut reader = decoder.read_info().expect("read PNG");
        let mut buf = vec![0; reader.output_buffer_size()];
        let info = reader.next_frame(&mut buf).expect("read PNG");
        let in_bytes = &buf[..info.buffer_size()];

        let mut path = PathBuf::from("../frames");
        path.push(file_entry.file_name());
        let file = File::create(path).expect("create output frame");
        let mut writer = BufWriter::new(file);
        let mut encoder = png::Encoder::new(&mut writer, WIDTH as u32, HEIGHT as u32);
        encoder.set_color(png::ColorType::Grayscale);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder.write_header().expect("write PNG");

        let mut out_bytes = vec![0; WIDTH * HEIGHT];

        for y in 0..HEIGHT {
            for x in 0..WIDTH {
                let value = to_linear[in_bytes[(y * WIDTH + x) * 3] as usize];
                let noise = noise_bytes[(y * WIDTH + x) * 4] as u16;

                let dithered_value = ((value as u16 * (HALFTONES - 1)) as f64 / 255.0
                    + noise as f64 / 256.0)
                    .floor() as u16
                    * 255
                    / (HALFTONES - 1);

                out_bytes[y * WIDTH + x] = from_linear[dithered_value as usize];
            }
        }

        writer.write_image_data(&out_bytes).expect("write PNG");
    }
}
