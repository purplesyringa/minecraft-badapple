use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Deserialize)]
pub struct Config {
    pub video: ConfigVideo,
    pub subpixels: ConfigSubpixels,
    pub frames_root: PathBuf,
    pub structures_root: String,
}

#[derive(Deserialize)]
pub struct ConfigVideo {
    pub width: usize,
    pub height: usize,
}

#[derive(Deserialize)]
pub struct ConfigSubpixels {
    pub width: usize,
    pub height: usize,
    pub distribution: Vec<Vec<usize>>,
}

#[derive(Serialize, Deserialize, PartialEq, Eq, Hash, Clone, Copy, Debug)]
pub struct Color(pub u8, pub u8, pub u8);
