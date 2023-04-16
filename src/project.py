from __future__ import annotations

import enum
import ntpath
import os
import posixpath
import typing as t
from pathlib import PurePosixPath, PureWindowsPath, Path

from pydantic import BaseModel, Field
from typing_extensions import Annotated, Literal


class ItemType(str, enum.Enum):
    Image = "YukkuriMovieMaker.Project.Items.ImageItem, YukkuriMovieMaker"
    Shape = "YukkuriMovieMaker.Project.Items.ShapeItem, YukkuriMovieMaker"
    Tachie = "YukkuriMovieMaker.Project.Items.TachieItem, YukkuriMovieMaker"
    Text = "YukkuriMovieMaker.Project.Items.TextItem, YukkuriMovieMaker"
    Voice = "YukkuriMovieMaker.Project.Items.VoiceItem, YukkuriMovieMaker"


class Animation(BaseModel):
    From: float = 0.0
    To: float = 0.0
    AnimationType: str = "なし"
    Span: float = 0.0

    @classmethod
    def const(cls, value: float) -> Animation:
        return cls(From=value)


class Decoration(BaseModel):
    Start: int = 0
    Length: int = 4
    IsBold: bool = False
    IsItalic: bool = False
    Scale: float = 1.0
    Font: t.Optional[str] = None
    Foreground: t.Optional[str] = None
    IsLineBreak: bool = False
    HasDecoration: bool = False


class AbstractItem(BaseModel):
    Type: ItemType = None
    Layer: int = 0
    X: Animation = Field(default_factory=Animation)
    Y: Animation = Field(default_factory=Animation)
    Opacity: Animation = Field(default_factory=lambda: Animation.const(100.0))
    Zoom: Animation = Field(default_factory=lambda: Animation.const(100.0))
    Rotation: Animation = Field(default_factory=Animation)
    Blend: str = "Normal"
    IsInverted: bool = False
    IsAlwaysOnTop: bool = False
    IsClippingWithObjectAbove: bool = False


class ItemBase(AbstractItem):
    Frame: int
    Length: int
    FadeIn: float = 0.0
    FadeOut: float = 0.0
    VideoEffects: t.List[t.Any] = Field(default_factory=list)
    Group: int = 0
    PlaybackRate: float = 100.0
    ContentOffset: str = "00:00:00"
    IsLocked: bool = False
    IsHidden: bool = False

    @classmethod
    def attrs_from_spec(
        cls, spec: "ItemSpec", layer: int, start_item: "Item", end_item: "Item"
    ) -> t.Dict[str, t.Any]:
        attrs = {
            "Layer": layer,
            "Frame": start_item.Frame,
            "Length": end_item.Frame + end_item.Length - start_item.Frame,
        }
        if spec.zoom:
            attrs["Zoom"] = Animation.const(spec.zoom)
        if spec.y:
            attrs["Y"] = Animation.const(spec.y)
        return attrs

    @classmethod
    def from_spec(cls, *args) -> Item:
        attrs = cls.attrs_from_spec(*args)
        return cls(**attrs)


class ImageItem(ItemBase):
    Type: Literal[ItemType.Image] = Field(ItemType.Image, alias="$type")
    FilePath: str

    @classmethod
    def attrs_from_spec(cls, project_root: Path, spec: "ImageSpec", *args) -> t.Dict[str, t.Any]:
        attrs = super().attrs_from_spec(spec, *args)
        attrs["FilePath"] = PureWindowsPath(project_root / spec.image)
        attrs["$type"] = ItemType.Image
        return attrs


class ShapeItem(ItemBase):
    Type: Literal[ItemType.Shape] = Field(ItemType.Shape, alias="$type")
    ShapeType: str = ""
    ShapeParameter: dict = Field(default_factory=dict)


class TachieItem(ItemBase):
    Type: Literal[ItemType.Tachie] = Field(ItemType.Tachie, alias="$type")
    CharacterName: str = ""
    TachieItemParameter: dict = Field(default_factory=dict)


class TextBase(BaseModel):
    Type: ItemType = None
    Font: str = "メイリオ"
    FontSize: Animation = Field(default_factory=lambda: Animation.const(48))
    LineHeight2: Animation = Field(default_factory=lambda: Animation.const(100))
    LetterSpacing2: Animation = Field(default_factory=Animation)
    DisplayInterval: float = 0.0
    BasePoint: str = "CenterCenter"
    FontColor: str = "#FF000000"
    Style: str = "Normal"
    StyleColor: str = "#FF000000"
    Bold: bool = False
    Italic: bool = False
    IsDevidedPerCharacter: bool = False


class DecoratedText(TextBase):
    Decorations: t.List[Decoration] = Field(default_factory=list)


class TextItem(ItemBase, DecoratedText):
    Type: Literal[ItemType.Text] = Field(ItemType.Text, alias="$type")
    Text: str

    @classmethod
    def attrs_from_spec(cls, spec: "TextSpec", *args) -> t.Dict[str, t.Any]:
        attrs = super().attrs_from_spec(spec, *args)
        attrs["Text"] = spec.text
        attrs["$type"] = ItemType.Text
        if spec.font_size:
            attrs["FontSize"] = Animation.const(spec.font_size)
        return attrs


class VoiceBase(BaseModel):
    Type: ItemType = None
    Volume: Animation = Field(default_factory=lambda: Animation.const(50))
    Pan: Animation = Field(default_factory=lambda: Animation.const(0))
    PlaybackRate: float = 100.0
    VoiceParameter: t.Dict[str, t.Any] = Field(default_factory=dict)
    VoiceFadeIn: float = 0.0
    VoiceFadeOut: float = 0.0
    EchoIsEnabled: bool = False
    EchoInterval: float = 0.1
    EchoAttenuation: float = 40.0
    JimakuFadeIn: float = 0.0
    JimakuFadeOut: float = 0.0
    JimakuVideoEffects: t.List[t.Any] = Field(default_factory=list)


class VoiceItem(ItemBase, VoiceBase):
    Type: Literal[ItemType.Voice] = Field(ItemType.Voice, alias="$type")
    CharacterName: str
    Serif: str
    IsWaveformEnabled: bool = False
    Hatsuon: str = ""
    Pronounce: t.Optional[str] = None
    VoiceLength: str = ""
    VoiceCache: t.Optional[str] = None
    ContentOffset: str = "00:00:00"
    JimakuVisibility: str = "UseCharacterSetting"
    TachieFaceParameter: t.Dict[str, t.Any] = Field(default_factory=dict)
    TachieFaceEffects: t.List[t.Any] = Field(default_factory=list)


class VideoInfo(BaseModel):
    FPS: int
    Hz: int
    Width: int
    Height: int


Item = Annotated[
    t.Union[ImageItem, ShapeItem, TachieItem, TextItem, VoiceItem],
    Field(discriminator="Type"),
]


class Timeline(BaseModel):
    VideoInfo: VideoInfo
    VerticalLine: t.Dict[str, t.Any]
    Items: t.List[Item]
    CurrentFrame: int
    LayerSettings: t.Dict[str, t.Any]
    Length: int
    MaxLayer: int


class SimpleTachieItemParameter(BaseModel):
    Type: str = Field(alias="$type")
    DefaultFace: str
    IsHiddenWhenNoSpeech: bool = False


class Character(AbstractItem, TextBase, VoiceBase):
    Name: str
    Color: str
    Voice: t.Dict[str, t.Any] = Field(default_factory=dict)
    AdditionalTime: float = 0.3
    CustomVoiceIsEnabled: bool = False
    CustomVoiceIncludeSubdirectories: bool = False
    CustomVoiceDirectory: str = ""
    CustomVoiceFileName: str = ""
    IsJimakuVisible: bool = True
    IsJimakuLocked: bool = False
    TachieType: str = "YukkuriMovieMaker.Plugin.Tachie.SimpleTachie.SimpleTachiePlugin"
    TachieCharacterParameter: t.Dict[str, t.Any] = Field(default_factory=dict)
    IsTachieLocked: bool = False
    TachieX: Animation = Field(default_factory=Animation)
    TachieY: Animation = Field(default_factory=Animation)
    TachieOpacity: Animation = Field(default_factory=Animation.const(100.0))
    TachieZoom: Animation = Field(default_factory=Animation.const(100.0))
    TachieRotation: Animation = Field(default_factory=Animation.const(0))
    TachieFadeIn: float = 0.0
    TachieFadeOut: float = 0.0
    TachieBlend: str = "Normal"
    TachieIsInverted: bool = False
    TachieIsAlwaysOnTop: bool = False
    TachieIsClippingWithObjectAbove: bool = False
    TachieDefaultItemParameter: SimpleTachieItemParameter
    TachieItemVideoEffects: t.List[t.Any] = Field(default_factory=list)
    TachieDefaultFaceParameter: t.Dict[str, t.Any] = Field(default_factory=dict)
    TachieDefaultFaceEffects: t.List[t.Any] = Field(default_factory=list)
    AdditionalForegroundTemplateName: t.Optional[str] = None
    AdditionalBackgroundTemplateName: t.Optional[str] = None


class Project(BaseModel):
    Timeline: Timeline
    Characters: t.List[Character]


# From https://stackoverflow.com/a/72064941
def dot_path(pth):
    """Return path str that may start with '.' if relative."""
    if pth.is_absolute():
        return os.fsdecode(pth)
    if isinstance(pth, PureWindowsPath):
        return ntpath.join(".", pth)
    elif isinstance(pth, PurePosixPath):
        return posixpath.join(".", pth)
    else:
        return os.path.join(".", pth)
