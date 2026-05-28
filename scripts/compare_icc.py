"""
对比英泽君预设 ICC 和我们生成的 ICC 的结构差异
"""
import struct
import os
import numpy as np

def parse_icc_full(path):
    with open(path, 'rb') as f:
        data = f.read()

    size = struct.unpack_from('>I', data, 0)[0]
    version = struct.unpack_from('>I', data, 8)[0]
    device_class = data[12:16].decode('ascii', errors='replace')
    color_space = data[16:20].decode('ascii', errors='replace')
    pcs = data[20:24].decode('ascii', errors='replace')

    tag_count = struct.unpack_from('>I', data, 128)[0]
    tags = {}
    for i in range(tag_count):
        offset = 132 + i * 12
        tag_sig = data[offset:offset+4].decode('ascii', errors='replace')
        tag_offset = struct.unpack_from('>I', data, offset+4)[0]
        tag_size = struct.unpack_from('>I', data, offset+8)[0]
        tags[tag_sig] = (tag_offset, tag_size)

    print("=" * 60)
    print("File:", os.path.basename(path))
    print("  Device class:", repr(device_class))
    print("  Color space:", repr(color_space))
    print("  PCS:", repr(pcs))
    print("  Version:", hex(version))
    print("  Tags:", list(tags.keys()))

    if 'A2B0' in tags:
        off, sz = tags['A2B0']
        lut_type = data[off:off+4].decode('ascii', errors='replace')
        if lut_type == 'mft2':
            in_ch = data[off+8]
            out_ch = data[off+9]
            grid = data[off+10]
            in_entries = struct.unpack_from('>H', data, off+48)[0]
            out_entries = struct.unpack_from('>H', data, off+50)[0]
            print(f"  A2B0 mft2: in={in_ch} out={out_ch} grid={grid} in_entries={in_entries} out_entries={out_entries}")

            # 读前几个 CLUT 值（跳过 header + in_tables）
            header_bytes = 52  # sig(4)+res(4)+channels(4)+matrix(36)+entries(4)
            in_table_bytes = in_ch * in_entries * 2
            clut_offset = off + header_bytes + in_table_bytes
            # 读前 3 个 CLUT 条目（对应 RGB=0,0,0 / 1/32,0,0 / 2/32,0,0）
            print("  CLUT first 3 entries (Lab uint16):")
            for i in range(3):
                L = struct.unpack_from('>H', data, clut_offset + i*6)[0]
                a = struct.unpack_from('>H', data, clut_offset + i*6 + 2)[0]
                b = struct.unpack_from('>H', data, clut_offset + i*6 + 4)[0]
                # decode
                L_f = L / 65535.0 * 100.0
                a_f = a / 65535.0 * 255.0 - 128.0
                b_f = b / 65535.0 * 255.0 - 128.0
                print(f"    [{i}] uint16=({L},{a},{b}) -> Lab=({L_f:.1f},{a_f:.1f},{b_f:.1f})")

            # 读最后一个 CLUT 条目（RGB=1,1,1）
            total_clut = grid**3
            last_off = clut_offset + (total_clut - 1) * out_ch * 2
            L = struct.unpack_from('>H', data, last_off)[0]
            a = struct.unpack_from('>H', data, last_off + 2)[0]
            b = struct.unpack_from('>H', data, last_off + 4)[0]
            L_f = L / 65535.0 * 100.0
            a_f = a / 65535.0 * 255.0 - 128.0
            b_f = b / 65535.0 * 255.0 - 128.0
            print(f"    [last=RGB(1,1,1)] uint16=({L},{a},{b}) -> Lab=({L_f:.1f},{a_f:.1f},{b_f:.1f})")

            # 读 in_table 前几个值
            print("  Input table first channel, first 4 values:")
            for i in range(min(4, in_entries)):
                v = struct.unpack_from('>H', data, off + 52 + i*2)[0]
                print(f"    [{i}] {v} ({v/65535:.4f})")

# 英泽君的 ICC（已知能在 C1 正常工作）
yingze_icc = os.path.expanduser(
    '~/Library/Application Support/Capture One/Styles/英泽君胶片预设合集/'
    '英泽君|理光经典正负片/RAW/英泽君|理光正负片 - 100%/'
    '英泽君的正片-普通.costyle.英泽君的正片-普通.icc'
)

# 我们生成的 ICC
our_icc = 'scripts/spektrafilm_test.icc'

if os.path.exists(yingze_icc):
    parse_icc_full(yingze_icc)
else:
    print("英泽君 ICC not found:", yingze_icc)

if os.path.exists(our_icc):
    parse_icc_full(our_icc)
else:
    print("Our ICC not found:", our_icc)
