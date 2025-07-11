import argparse
import os
import numpy as np
import math

import torchvision.transforms as transforms
from torchvision.utils import save_image

from torch.utils.data import DataLoader
from torchvision import datasets
from torch.autograd import Variable

import torch.nn as nn
import torch.nn.functional as F
import torch


class UNet(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=True):
        super(UNet, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = Down(512, 1024 // factor)
        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)
        self.outc = OutConv(64, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class Generator_main(nn.Module):
    def __init__(self, input_channels, n_filters, n_classes, bilinear=False):
        super(Generator_main, self).__init__()

        self.n_channels = input_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(input_channels, n_filters)
        self.down1 = Down(n_filters, 2 * n_filters)
        self.down2 = Down(2 * n_filters, 4 * n_filters)
        self.down3 = Down(4 * n_filters, 8 * n_filters)
        self.down4 = Down(8 * n_filters, 16 * n_filters)

        self.downsample = nn.MaxPool2d(2)

        self.up1 = Up_new(16 * n_filters, 8 * n_filters, bilinear)
        self.S1 = side_one(8 * n_filters, n_classes)

        self.up2 = Up_new(8 * n_filters, 4 * n_filters, bilinear)
        self.S2 = side_two(4 * n_filters, n_classes)

        self.up3 = Up_new(4 * n_filters, 2 * n_filters, bilinear)
        self.S3 = side_three(2 * n_filters, n_classes)

        self.up4 = Up_new(2 * n_filters, 1 * n_filters, bilinear)

        # self.outc = OutConv((n_filters+8), n_classes)
        self.outc = OutConv((n_filters), n_classes)

    def forward(self, x, x_a, x_v):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        s1 = self.S1(x)
        x = self.up2(x, x3)
        s2 = self.S2(x)

        # x = torch.cat([x_a, x, x_v], dim=1)
        x = self.up3(x, x2)
        s3 = self.S3(x)
        x = self.up4(x, x1)

        x_fusion = torch.mean(torch.stack([x_a, x, x_v], dim=0), dim=0)
        logits = self.outc(x_fusion)
        # logits = self.outc(x)

        return logits, s1, s2, s3


class Generator_branch(nn.Module):
    def __init__(self, input_channels, n_filters, n_classes, bilinear=False):
        super(Generator_branch, self).__init__()

        self.n_channels = input_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(input_channels, n_filters)
        self.down1 = Down(n_filters, 2 * n_filters)
        self.down2 = Down(2 * n_filters, 4 * n_filters)
        self.down3 = Down(4 * n_filters, 8 * n_filters)
        self.down4 = Down(8 * n_filters, 16 * n_filters)

        self.up1 = Up_new(16 * n_filters, 8 * n_filters, bilinear)
        self.up2 = Up_new(8 * n_filters, 4 * n_filters, bilinear)
        self.up3 = Up_new(4 * n_filters, 2 * n_filters, bilinear)
        self.up4 = Up_new(2 * n_filters, 1 * n_filters, bilinear)
        self.outc = OutConv(n_filters, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x_final = self.up4(x, x1)
        logits = self.outc(x_final)
        return logits, x_final


class Discriminator(nn.Module):
    def __init__(self, input_channels, n_filters, n_classes, bilinear=True):
        super(Discriminator, self).__init__()

        self.n_channels = input_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(input_channels, n_filters)
        self.down1 = Down(n_filters, 2 * n_filters)
        self.down2 = Down(2 * n_filters, 4 * n_filters)
        self.down3 = Down(4 * n_filters, 8 * n_filters)
        self.down4 = Down(8 * n_filters, 16 * n_filters)

        self.up1 = Up(16 * n_filters, 8 * n_filters, bilinear)
        self.up2 = Up(8 * n_filters, 4 * n_filters, bilinear)
        self.up3 = Up(4 * n_filters, 2 * n_filters, bilinear)
        self.up4 = Up(2 * n_filters, 1 * n_filters, bilinear)
        self.outc = OutConv(n_filters, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class DoubleConv(nn.Module):
    """(convolution => [BN] => ReLU) * 2"""

    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        mid_channels = out_channels
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    """Downscaling with maxpool then double conv"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2), DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.maxpool_conv(x)


class Up(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()

        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels)

        else:
            self.conv_bottom = bottom_conv(in_channels, out_channels)
            self.up = nn.Upsample(scale_factor=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.conv_bottom(x1)
        x1 = self.up(x1)
        # input is CHW
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]

        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])

        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class bottom_conv(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        mid_channels = out_channels
        if not mid_channels:
            mid_channels = out_channels
        self.single_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.single_conv(x)


class DoubleAdd(nn.Module):
    """(convolution => [BN] => ReLU) * 2"""

    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.activation = nn.Sequential(
            nn.BatchNorm2d(out_channels // 2),
            nn.ReLU(inplace=True),
        )

    def forward(self, x1, x2):
        n, c, h, w = list(x1.size())
        x1 = torch.reshape(input=x1, shape=(n, c // 2, 2, h, w))
        x1 = x1.sum(dim=2)
        x1 = self.activation(x1)

        n, c, h, w = list(x2.size())
        x2 = torch.reshape(input=x2, shape=(n, c // 2, 2, h, w))
        x2 = x2.sum(dim=2)
        x2 = self.activation(x2)
        return torch.cat([x1, x2], dim=1)


class Up_new(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()
        self.conv_bottom = bottom_conv(in_channels, out_channels)
        self.up = nn.Upsample(scale_factor=2)
        self.add = DoubleAdd(in_channels, out_channels)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x = self.conv_bottom(x1)
        x = self.up(x)
        # road 1

        x_1 = self.add(x, x2)

        # road 2
        x_2 = torch.cat([x, x2], dim=1)
        x_2 = self.conv(x_2)

        return torch.add(x_1, x_2)


class Side_block(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()
        self.block = nn.Sequential(
            nn.Upsample(scale_factor=2),
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class side_one(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()

        self.side_block_1 = Side_block(in_channels, in_channels // 2)
        self.side_block_2 = Side_block(in_channels // 2, in_channels // 4)
        self.side_block_3 = Side_block(in_channels // 4, in_channels // 8)
        self.side_output = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x):
        x = self.side_block_1(x)
        x = self.side_block_2(x)
        x = self.side_block_3(x)
        x = self.side_output(x)

        return x


class side_two(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()

        self.side_block_1 = Side_block(in_channels, in_channels // 2)
        self.side_block_2 = Side_block(in_channels // 2, in_channels // 4)
        self.side_output = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x):
        x = self.side_block_1(x)
        x = self.side_block_2(x)
        x = self.side_output(x)

        return x


class side_three(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=False):
        super().__init__()

        self.side_block_1 = Side_block(in_channels, in_channels // 2)
        self.side_output = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x):
        x = self.side_block_1(x)
        x = self.side_output(x)

        return x


class OutConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(OutConv, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)
