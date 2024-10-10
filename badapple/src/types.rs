use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
pub struct Config {
    pub video: ConfigVideo,
    pub pixel: ConfigPixel,
    pub superpixel: ConfigSuperpixel,
    pub structures_root: String,
    pub colors: Vec<Color>,
    pub predictions: usize,
}

#[derive(Deserialize)]
pub struct ConfigVideo {
    pub width: usize,
    pub height: usize,
}

#[derive(Deserialize)]
pub struct ConfigPixel {
    pub width: usize,
    pub height: usize,
}

#[derive(Deserialize)]
pub struct ConfigSuperpixel {
    pub width: usize,
    pub height: usize,
}

#[derive(Serialize, Deserialize, PartialEq, Eq, Hash, Clone, Copy, Debug)]
pub struct Color(pub u8, pub u8, pub u8);

#[derive(Serialize, Deserialize)]
pub struct Prediction {
    pub from: Vec<Color>,
    pub to: Vec<Color>,
}
