# Bad Apple!! in Minecraft

This repository contains most of the tools I used while building Bad Apple!! in Minecraft. This is a dump rather than an open-source project, so don't expect support, good code quality, or elaborate instructions.

Read the post on this project: [We built the best Bad Apple!! in Minecraft](https://purplesyringa.moe/blog/we-built-the-best-bad-apple-in-minecraft/).

Here's a very high-level explanation of the files in this repo:

- `config.json` specifies various information about the video and the Minecraft world
- `independent_*.json` files specify blockstates; no need to touch these unless you need to remove some blocks from there because you want to use them for decoration
- Other JSON files are auxiliary assets, generated by scripts
- `badapple` is a Rust crate with multiply binaries, invoked with `cargo run --release --bin <binary_name>`
- `.py` files are Python scripts, using packages specified in `requirements.txt`

To prepare a video, you need to, in order:

- Put the frames to the `frames` directory as PNGs
- Invoke the `dither` Rust script
- Invoke the `predict_superpixels` Rust script
- Invoke the `generate_pixels` Python script
- Invoke the `render_frames` Rust script

This should generate the structures and fill the resource pack. For release, you then need to compress the resource pack and put it to `resources.zip` in the world directory.

`utils.py` generates instant structstone wire. Redstone is left as an exercise to the reader (consult the original world for that).
