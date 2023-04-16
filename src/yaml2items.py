from __future__ import annotations

import argparse
import json
import typing as t
from pathlib import Path

import yaml
from PIL import Image
from pydantic import BaseModel, Field, validator

from .project import ImageItem, ItemType, Project, TextItem, VoiceItem


class VoiceSpec(BaseModel):
    character: str
    text: str

    @validator("text")
    def validate_text(cls, value: str) -> str:
        return value.strip()

    def matches(self, other: VoiceItem) -> bool:
        if self.character != other.CharacterName:
            return False
        if self.text != other.Serif:
            return False
        return True


class ItemSpec(BaseModel):
    zoom: t.Optional[float]
    y: t.Optional[float]
    start_voice_spec: t.Optional[VoiceSpec]
    end_voice_spec: t.Optional[VoiceSpec]


class ImageSpec(ItemSpec):
    image: str


class TextSpec(ItemSpec):
    text: str
    font_size: t.Optional[float]


def main(yaml_path: Path, ymmp_path: Path, output_path: Path):
    lines = yaml.safe_load(yaml_path.read_text())
    item_specs = list(list_item_specs(lines))
    project = Project.parse_obj(json.loads(ymmp_path.read_text(encoding="utf-8-sig")))
    project_root = Path(os.environ.get("PROJECT_ROOT", output_path.parent))
    layer = 3
    for item in project.Timeline.Items:
        if item.Layer >= layer:
            item.Layer += 1
    voice_items = [
        item for item in project.Timeline.Items if item.Type == ItemType.Voice
    ]
    while len(item_specs) and len(voice_items):
        current_item_spec = item_specs.pop(0)
        while voice_items and not current_item_spec.start_voice_spec.matches(
            voice_items[0]
        ):
            voice_items.pop(0)
        if not voice_items:
            raise ValueError(
                f"No matching voice item for {current_item_spec.start_voice_spec}"
            )
        start_voice_item = voice_items[0]
        while voice_items and not current_item_spec.end_voice_spec.matches(
            voice_items[0]
        ):
            voice_items.pop(0)
        if not voice_items:
            raise ValueError(
                f"No matching voice item for {current_item_spec.end_voice_spec}"
            )
        end_voice_item = voice_items.pop(0)
        if isinstance(current_item_spec, ImageSpec):
            transform = calculate_image_transformation(
                Path(current_item_spec.image), project.Timeline.VideoInfo, 320, 20
            )
            if current_item_spec.zoom is None:
                current_item_spec.zoom = transform.zoom
            if current_item_spec.y is None:
                current_item_spec.y = transform.y
            new_item = ImageItem.from_spec(
                project_root, current_item_spec, layer, start_voice_item, end_voice_item
            )
        elif isinstance(current_item_spec, TextSpec):
            new_item = TextItem.from_spec(
                current_item_spec, layer, start_voice_item, end_voice_item
            )
        if new_item:
            project.Timeline.Items.append(new_item.dict(by_alias=True))

    for item in project.Timeline.Items:
        print(
            getattr(item, "Type") if hasattr(item, "Type") else item["$type"],
            getattr(item, "Frame") if hasattr(item, "Frame") else item["Frame"],
            getattr(item, "CharacterName", "n/a"),
            getattr(item, "FilePath", "n/a"),
        )

    with output_path.open("w", encoding="utf-8-sig") as f:
        json.dump(project.dict(by_alias=True), f, indent=2, ensure_ascii=False)


class ImageTransformation(BaseModel):
    zoom: int = 0
    y: int = 0


def calculate_image_transformation(
    image_path: Path, video_info: VideoInfo, bottom_margin: int, margin: int
) -> ImageTransformation:
    image = Image.open(image_path.resolve())
    image_width, image_height = image.size

    transform = ImageTransformation()

    transform.y = bottom_margin * -0.5

    width_zoom = (video_info.Width - margin) / image_width
    height_zoom = (video_info.Height - margin - bottom_margin) / image_height
    transform.zoom = 100 * min(width_zoom, height_zoom)
    assert transform.zoom * image_height / 100 < video_info.Height - bottom_margin
    assert transform.zoom * image_width / 100 < video_info.Width

    return transform


def list_item_specs(lines: t.List[dict]):
    current_item = None
    last_voice_spec = None
    for line in lines:
        if "image" in line or "text" in line:
            if current_item:
                if last_voice_spec:
                    current_item.end_voice_spec = last_voice_spec
                if not current_item.end_voice_spec:
                    current_item.end_voice_spec = current_item.start_voice_spec
                assert (
                    current_item.start_voice_spec and current_item.end_voice_spec
                ), current_item
                yield current_item
            if "image" in line:
                current_item = ImageSpec.parse_obj(line)
            elif "text" in line:
                current_item = TextSpec.parse_obj(line)
            last_voice_spec = None
            continue
        if not current_item:
            continue
        if not line or not isinstance(line, dict):
            continue
        key, value = list(line.items())[0]
        voice_spec = VoiceSpec(character=key, text=value)
        if not current_item.start_voice_spec:
            current_item.start_voice_spec = voice_spec
            continue
        last_voice_spec = voice_spec

    if current_item:
        if last_voice_spec:
            current_item.end_voice_spec = last_voice_spec
        assert current_item.start_voice_spec and current_item.end_voice_spec
        yield current_item


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_yaml", type=Path)
    parser.add_argument("draft_ymmp", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    main(args.source_yaml, args.draft_ymmp, args.output_path)
