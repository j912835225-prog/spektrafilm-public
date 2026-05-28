import struct
import os

def parse_icc(path):
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

    print("File:", os.path.basename(path))
    print("  Size:", size, "bytes")
    print("  Version:", hex(version))
    print("  Device class:", repr(device_class))
    print("  Color space:", repr(color_space))
    print("  PCS:", repr(pcs))
    print("  Tags:", list(tags.keys()))

    for lut_tag in ['A2B0', 'A2B1', 'B2A0']:
        if lut_tag in tags:
            off, sz = tags[lut_tag]
            lut_type = data[off:off+4].decode('ascii', errors='replace')
            # mft2: grid points at byte 10
            if lut_type == 'mft2':
                grid = data[off+10]
                in_ch = data[off+8]
                out_ch = data[off+9]
                print("  " + lut_tag + ": type=mft2 grid=" + str(grid) + " in=" + str(in_ch) + " out=" + str(out_ch) + " size=" + str(sz))
            elif lut_type == 'mAB ':
                print("  " + lut_tag + ": type=mAB  size=" + str(sz))
            else:
                print("  " + lut_tag + ": type=" + repr(lut_type) + " size=" + str(sz))

    for trc in ['rTRC', 'gTRC', 'bTRC']:
        if trc in tags:
            off, sz = tags[trc]
            trc_type = data[off:off+4].decode('ascii', errors='replace')
            print("  " + trc + ": type=" + repr(trc_type) + " size=" + str(sz))

    for tag in ['rXYZ', 'gXYZ', 'bXYZ', 'wtpt']:
        if tag in tags:
            off, sz = tags[tag]
            # XYZ value
            x = struct.unpack_from('>i', data, off+8)[0] / 65536.0
            y = struct.unpack_from('>i', data, off+12)[0] / 65536.0
            z = struct.unpack_from('>i', data, off+16)[0] / 65536.0
            print("  " + tag + ": XYZ=(" + str(round(x,4)) + ", " + str(round(y,4)) + ", " + str(round(z,4)) + ")")
    print()

# Capture One 自己的相机 input profile
c1_profiles = [
    '/Applications/Capture One.app/Contents/Frameworks/ImageProcessing.framework/Versions/A/Resources/Profiles/Input/NikonZ6-Generic.icm',
    '/Applications/Capture One.app/Contents/Frameworks/ImageProcessing.framework/Versions/A/Resources/Profiles/Input/FujiXT4-Generic.icm',
    '/Applications/Capture One.app/Contents/Frameworks/ImageProcessing.framework/Versions/A/Resources/Profiles/Input/NikonD750-Nikon - Standard.icm',
]
for p in c1_profiles:
    if os.path.exists(p):
        parse_icc(p)
