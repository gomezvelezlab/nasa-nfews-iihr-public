"""
Standalone PyTorch implementation of the IBM-NASA Prithvi-EO-1.0-100M
multi-temporal crop classification model.

Why this file exists: the official release ships inference code built on the
legacy mmcv / mmsegmentation stack, which is painful to install on Colab or a
JupyterHub. This module reproduces the released checkpoint exactly using only
torch and numpy, so `pip install torch` is the whole setup.

Architecture (matches the published fine-tune):
    TemporalViTEncoder (6 blocks, embed 768, 8 heads, patch 16, 3 frames)
      -> ConvTransformerTokensToEmbeddingNeck (tokens -> 2304 ch, 14x14 -> 224x224)
      -> FCNHead (2304 -> 256 -> 13 classes)

Input:  (B, 6, 3, 224, 224)  = 6 HLS bands x 3 growing-season dates, normalized
Output: (B, 13, 224, 224)    class logits

Bands, in this order (HLS S30 names):
    B02 Blue, B03 Green, B04 Red, B8A Narrow NIR, B11 SWIR 1, B12 SWIR 2

Model card: https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification
"""
from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Constants from the official fine-tuning config
# (multi_temporal_crop_classification_Prithvi_100M.py)
# ---------------------------------------------------------------------------
NUM_FRAMES = 3
NUM_BANDS = 6
IMG_SIZE = 224
PATCH_SIZE = 16
EMBED_DIM = 768
DEPTH = 6
NUM_HEADS = 8
MLP_RATIO = 4.0
NUM_CLASSES = 13
SLIDE_STRIDE = 112  # test_cfg stride from the config

# Per-band normalization (repeated for each of the 3 time steps)
MEANS = np.array([494.905781, 815.239594, 924.335066,
                  2968.881459, 2634.621962, 1739.579917], dtype=np.float32)
STDS = np.array([284.925432, 357.84876, 575.566823,
                 896.601013, 951.900334, 921.407808], dtype=np.float32)

from .classes import CLASSES, CLASS_COLORS  # noqa: F401


# ---------------------------------------------------------------------------
# Positional embedding (3D sin-cos, as in the original geospatial_fm code)
# ---------------------------------------------------------------------------
def _get_1d_sincos_pos_embed_from_grid(embed_dim: int, pos: np.ndarray) -> np.ndarray:
    omega = np.arange(embed_dim // 2, dtype=np.float32)
    omega /= embed_dim / 2.0
    omega = 1.0 / 10000 ** omega
    pos = pos.reshape(-1)
    out = np.einsum("m,d->md", pos, omega)
    return np.concatenate([np.sin(out), np.cos(out)], axis=1)


def get_3d_sincos_pos_embed(embed_dim: int, grid_size: Tuple[int, int, int],
                            cls_token: bool = False) -> np.ndarray:
    t, h, w = grid_size
    w_dim = embed_dim // 16 * 6
    h_dim = embed_dim // 16 * 6
    t_dim = embed_dim // 16 * 4
    w_pos = _get_1d_sincos_pos_embed_from_grid(w_dim, np.arange(w))
    h_pos = _get_1d_sincos_pos_embed_from_grid(h_dim, np.arange(h))
    t_pos = _get_1d_sincos_pos_embed_from_grid(t_dim, np.arange(t))
    w_pos = np.tile(w_pos, (t * h, 1))
    h_pos = np.tile(np.repeat(h_pos, w, axis=0), (t, 1))
    t_pos = np.repeat(t_pos, h * w, axis=0)
    pos = np.concatenate((w_pos, h_pos, t_pos), axis=1)
    if cls_token:
        pos = np.concatenate([np.zeros([1, embed_dim]), pos], axis=0)
    return pos


# ---------------------------------------------------------------------------
# Transformer building blocks (timm-compatible key names)
# ---------------------------------------------------------------------------
class Mlp(nn.Module):
    def __init__(self, dim: int, hidden: int):
        super().__init__()
        self.fc1 = nn.Linear(dim, hidden)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden, dim)

    def forward(self, x):
        return self.fc2(self.act(self.fc1(x)))


class Attention(nn.Module):
    def __init__(self, dim: int, num_heads: int):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim)

    def forward(self, x):
        B, N, C = x.shape
        qkv = (self.qkv(x)
               .reshape(B, N, 3, self.num_heads, self.head_dim)
               .permute(2, 0, 3, 1, 4))
        q, k, v = qkv.unbind(0)
        x = F.scaled_dot_product_attention(q, k, v)  # matches softmax(qk^T*scale)v
        x = x.transpose(1, 2).reshape(B, N, C)
        return self.proj(x)


class Block(nn.Module):
    def __init__(self, dim: int, num_heads: int, mlp_ratio: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = Attention(dim, num_heads)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = Mlp(dim, int(dim * mlp_ratio))

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x


class PatchEmbed(nn.Module):
    """3D patch embedding: (B, C, T, H, W) -> (B, T*H/16*W/16, embed)."""

    def __init__(self, img_size=IMG_SIZE, patch_size=PATCH_SIZE,
                 num_frames=NUM_FRAMES, tubelet_size=1,
                 in_chans=NUM_BANDS, embed_dim=EMBED_DIM):
        super().__init__()
        self.img_size = (img_size, img_size)
        self.grid_size = (num_frames // tubelet_size,
                          img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1] * self.grid_size[2]
        self.proj = nn.Conv3d(in_chans, embed_dim,
                              kernel_size=(tubelet_size, patch_size, patch_size),
                              stride=(tubelet_size, patch_size, patch_size))

    def forward(self, x):
        x = self.proj(x)                      # B, E, T, Hp, Wp
        x = x.flatten(2).transpose(1, 2)      # B, T*Hp*Wp, E
        return x


class TemporalViTEncoder(nn.Module):
    def __init__(self, depth=DEPTH, num_heads=NUM_HEADS):
        super().__init__()
        self.patch_embed = PatchEmbed()
        num_patches = self.patch_embed.num_patches
        self.cls_token = nn.Parameter(torch.zeros(1, 1, EMBED_DIM))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, EMBED_DIM),
                                      requires_grad=False)
        self.blocks = nn.ModuleList(
            [Block(EMBED_DIM, num_heads, MLP_RATIO) for _ in range(depth)])
        self.norm = nn.LayerNorm(EMBED_DIM)
        # init fixed sin-cos pos embed (overwritten by checkpoint anyway)
        pe = get_3d_sincos_pos_embed(EMBED_DIM, self.patch_embed.grid_size, True)
        self.pos_embed.data.copy_(torch.from_numpy(pe).float().unsqueeze(0))

    def forward(self, x):
        x = self.patch_embed(x)
        x = x + self.pos_embed[:, 1:, :]
        cls_tok = (self.cls_token + self.pos_embed[:, :1, :]).expand(x.shape[0], -1, -1)
        x = torch.cat((cls_tok, x), dim=1)
        for blk in self.blocks:
            x = blk(x)
        return self.norm(x)


class Norm2d(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.ln = nn.LayerNorm(dim, eps=1e-6)

    def forward(self, x):
        x = x.permute(0, 2, 3, 1)
        x = self.ln(x)
        return x.permute(0, 3, 1, 2).contiguous()


class ConvTransformerTokensToEmbeddingNeck(nn.Module):
    """Tokens (B, 1+3*196, 768) -> feature map (B, 2304, 224, 224)."""

    def __init__(self, embed_dim=EMBED_DIM * NUM_FRAMES,
                 output_embed_dim=EMBED_DIM * NUM_FRAMES, hp=14, wp=14):
        super().__init__()
        self.hp, self.wp = hp, wp
        self.output_embed_dim = output_embed_dim
        k = dict(kernel_size=2, stride=2)
        self.fpn1 = nn.Sequential(
            nn.ConvTranspose2d(embed_dim, output_embed_dim, **k),
            Norm2d(output_embed_dim),
            nn.GELU(),
            nn.ConvTranspose2d(output_embed_dim, output_embed_dim, **k),
        )
        self.fpn2 = nn.Sequential(
            nn.ConvTranspose2d(output_embed_dim, output_embed_dim, **k),
            Norm2d(output_embed_dim),
            nn.GELU(),
            nn.ConvTranspose2d(output_embed_dim, output_embed_dim, **k),
        )

    def forward(self, x):
        x = x[:, 1:, :]                                   # drop cls token
        x = x.permute(0, 2, 1).reshape(x.shape[0], -1, self.hp, self.wp)
        x = self.fpn1(x)
        x = self.fpn2(x)
        return x


class FCNHead(nn.Module):
    """mmseg FCNHead with num_convs=1, concat_input=False (BN, key-compatible)."""

    class ConvModule(nn.Module):
        def __init__(self, cin, cout):
            super().__init__()
            self.conv = nn.Conv2d(cin, cout, 3, padding=1, bias=False)
            self.bn = nn.BatchNorm2d(cout)
            self.activate = nn.ReLU(inplace=True)

        def forward(self, x):
            return self.activate(self.bn(self.conv(x)))

    def __init__(self, in_channels=EMBED_DIM * NUM_FRAMES, channels=256,
                 num_classes=NUM_CLASSES, num_convs=1, dropout_ratio=0.1):
        super().__init__()
        convs = []
        for i in range(num_convs):
            convs.append(self.ConvModule(in_channels if i == 0 else channels, channels))
        self.convs = nn.Sequential(*convs)
        self.dropout = nn.Dropout2d(dropout_ratio)
        self.conv_seg = nn.Conv2d(channels, num_classes, 1)

    def forward(self, x):
        x = self.convs(x)
        x = self.dropout(x)
        return self.conv_seg(x)


class PrithviCropClassifier(nn.Module):
    """backbone + neck + decode_head (aux head only used during training)."""

    def __init__(self):
        super().__init__()
        self.backbone = TemporalViTEncoder()
        self.neck = ConvTransformerTokensToEmbeddingNeck()
        self.decode_head = FCNHead(num_convs=1)
        self.auxiliary_head = FCNHead(num_convs=2)  # present in ckpt; unused at inference

    def forward(self, x):
        """x: (B, 6, 3, 224, 224) normalized -> logits (B, 13, 224, 224)."""
        tokens = self.backbone(x)
        feats = self.neck(tokens)
        return self.decode_head(feats)


# ---------------------------------------------------------------------------
# Checkpoint loading
# ---------------------------------------------------------------------------
def load_model(checkpoint_path: str, device: str = "cpu",
               verbose: bool = True) -> PrithviCropClassifier:
    """Build the model and load the official mmseg checkpoint into it (strict)."""
    try:
        ckpt = torch.load(checkpoint_path, map_location="cpu", mmap=True,
                          weights_only=False)
    except TypeError:  # older torch without mmap arg
        ckpt = torch.load(checkpoint_path, map_location="cpu")
    state = ckpt.get("state_dict", ckpt)

    model = PrithviCropClassifier()
    missing, unexpected = model.load_state_dict(state, strict=False)
    # num_batches_tracked buffers may be absent in old checkpoints - that is fine
    real_missing = [k for k in missing if not k.endswith("num_batches_tracked")]
    allowed_unexpected = [k for k in unexpected
                          if not (k.startswith("backbone.") or k.startswith("neck.")
                                  or k.startswith("decode_head.")
                                  or k.startswith("auxiliary_head."))]
    if real_missing:
        raise RuntimeError(f"Missing keys when loading checkpoint: {real_missing}")
    if verbose:
        n_loaded = len(state) - len(unexpected)
        print(f"[model] loaded {n_loaded}/{len(state)} tensors from checkpoint "
              f"({len(unexpected)} unused: {unexpected[:4]}...)" if unexpected else
              f"[model] loaded all {n_loaded} tensors from checkpoint")
        if allowed_unexpected:
            print(f"[model] note - unrecognized keys ignored: {allowed_unexpected[:8]}")
    model.eval().to(device)
    return model


# ---------------------------------------------------------------------------
# Preprocessing + sliding-window inference
# ---------------------------------------------------------------------------
def normalize(img18: np.ndarray) -> np.ndarray:
    """(18, H, W) raw HLS reflectance (x10000 scaling) -> normalized float32."""
    means = np.tile(MEANS, NUM_FRAMES)[:, None, None]
    stds = np.tile(STDS, NUM_FRAMES)[:, None, None]
    return (img18.astype(np.float32) - means) / stds


@torch.no_grad()
def predict(model: PrithviCropClassifier, img18: np.ndarray,
            nodata_mask: np.ndarray | None = None,
            stride: int = SLIDE_STRIDE, device: str = "cpu",
            progress: bool = True) -> np.ndarray:
    """Sliding-window inference on an 18-band image of arbitrary size.

    img18: (18, H, W) RAW (unnormalized) reflectance values.
    nodata_mask: optional (H, W) bool, True where invalid.
    Returns (H, W) uint8 class map, values 1..13 (0 = nodata).
    """
    assert img18.ndim == 3 and img18.shape[0] == NUM_BANDS * NUM_FRAMES, \
        f"expected (18, H, W), got {img18.shape}"
    x = normalize(img18)
    _, H, W = x.shape

    # pad to at least 224 x 224 (in normalized space, 0 == band mean)
    pad_h, pad_w = max(0, IMG_SIZE - H), max(0, IMG_SIZE - W)
    if pad_h or pad_w:
        x = np.pad(x, ((0, 0), (0, pad_h), (0, pad_w)), mode="constant")
    _, Hp, Wp = x.shape

    xt = torch.from_numpy(x).to(device)
    xt = xt.reshape(NUM_BANDS, NUM_FRAMES, Hp, Wp).unsqueeze(0)  # 18,H,W -> 6,3,H,W

    logits_sum = torch.zeros(1, NUM_CLASSES, Hp, Wp, device=device)
    counts = torch.zeros(1, 1, Hp, Wp, device=device)

    ys = list(range(0, max(Hp - IMG_SIZE, 0) + 1, stride))
    xs = list(range(0, max(Wp - IMG_SIZE, 0) + 1, stride))
    if ys[-1] != Hp - IMG_SIZE:
        ys.append(Hp - IMG_SIZE)
    if xs[-1] != Wp - IMG_SIZE:
        xs.append(Wp - IMG_SIZE)

    total = len(ys) * len(xs)
    done = 0
    for y0 in ys:
        for x0 in xs:
            tile = xt[:, :, :, y0:y0 + IMG_SIZE, x0:x0 + IMG_SIZE]
            out = model(tile)
            logits_sum[:, :, y0:y0 + IMG_SIZE, x0:x0 + IMG_SIZE] += out
            counts[:, :, y0:y0 + IMG_SIZE, x0:x0 + IMG_SIZE] += 1
            done += 1
            if progress and (done % 10 == 0 or done == total):
                print(f"\r[inference] window {done}/{total}", end="", flush=True)
    if progress:
        print()

    logits = logits_sum / counts
    pred = logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8) + 1
    pred = pred[:H, :W]
    if nodata_mask is not None:
        pred[nodata_mask] = 0
    return pred


def class_areas(pred: np.ndarray, pixel_m: float = 30.0) -> List[dict]:
    """Per-class pixel counts / hectares for a prediction map."""
    rows = []
    total_valid = int((pred > 0).sum())
    for cid, name in enumerate(CLASSES, start=1):
        n = int((pred == cid).sum())
        if n == 0:
            continue
        rows.append(dict(class_id=cid, name=name, pixels=n,
                         hectares=round(n * pixel_m * pixel_m / 10_000, 1),
                         pct_of_valid=round(100 * n / max(total_valid, 1), 2)))
    return sorted(rows, key=lambda r: -r["pixels"])
