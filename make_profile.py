#!/usr/bin/env python3
"""Build an ICC v2 matrix/TRC display profile with a vcgt tint correction.

Panel values come from the Dell G16 EDID (AUO 0x3CA2). Only the standard library
is needed. The tint correction is stored in the vcgt tag, because KWin ignores
white point shifts made through the colorants but applies vcgt.

Usage:
    ./make_profile.py                       # final values, writes ./AUO3CA2_Dell_G16_final.icc
    ./make_profile.py -r 0.95 -g 0.94       # custom gains
    ./make_profile.py -o /path/out.icc
"""
import argparse
import datetime
import struct

# EDID chromaticities (x, y) and gamma of the built-in panel
RED = (0.6796, 0.3203)
GREEN = (0.2646, 0.6845)
BLUE = (0.1445, 0.0546)
WHITE = (0.3134, 0.3291)
GAMMA = 2.2

D50 = (0.9642, 1.0, 0.8249)
BRADFORD = ((0.8951, 0.2664, -0.1614), (-0.7502, 1.7135, 0.0367), (0.0389, -0.0685, 1.0296))
BRADFORD_INV = ((0.9869929, -0.1470543, 0.1599627), (0.4323053, 0.5183603, 0.0492912),
                (-0.0085287, 0.0400428, 0.9684867))

DEFAULT_GAINS = (0.955, 0.9425, 1.0)  # final values: exact midpoint of variants a and b


def mat_vec(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def mat_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def inverse(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return ((e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det), \
           ((f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det), \
           ((d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det)


def xy_to_xyz(x, y):
    return (x / y, 1.0, (1 - x - y) / y)


def colorants_d50():
    """RGB->XYZ colorants for the EDID primaries, Bradford-adapted to D50."""
    p = [xy_to_xyz(*c) for c in (RED, GREEN, BLUE)]
    cols = ((p[0][0], p[1][0], p[2][0]), (p[0][1], p[1][1], p[2][1]), (p[0][2], p[1][2], p[2][2]))
    s = mat_vec(inverse(cols), xy_to_xyz(*WHITE))
    m = tuple(tuple(cols[i][j] * s[j] for j in range(3)) for i in range(3))
    src, dst = mat_vec(BRADFORD, xy_to_xyz(*WHITE)), mat_vec(BRADFORD, D50)
    scale = ((dst[0] / src[0], 0, 0), (0, dst[1] / src[1], 0), (0, 0, dst[2] / src[2]))
    adapt = mat_mul(BRADFORD_INV, mat_mul(scale, BRADFORD))
    return mat_mul(adapt, m)


def s15(v):
    return struct.pack('>i', int(round(v * 65536)))


def xyz_tag(v):
    return b'XYZ \0\0\0\0' + b''.join(s15(c) for c in v)


def text_tag(t):
    return b'text\0\0\0\0' + t.encode() + b'\0'


def desc_tag(t):
    a = t.encode() + b'\0'
    return b'desc\0\0\0\0' + struct.pack('>I', len(a)) + a + b'\0' * 8 + struct.pack('>HB', 0, 0) + b'\0' * 67


def curv_tag(g):
    return b'curv\0\0\0\0' + struct.pack('>IH', 1, int(round(g * 256))) + b'\0\0'


def vcgt_tag(gains):
    d = b'vcgt\0\0\0\0' + struct.pack('>IHHH', 0, 3, 256, 2)
    for gain in gains:
        d += b''.join(struct.pack('>H', int(round(i / 255 * gain * 65535))) for i in range(256))
    return d


def build(gains, name):
    m = colorants_d50()
    tags = [
        ('desc', desc_tag(name)),
        ('cprt', text_tag('Generated from EDID, tint-adjusted')),
        ('wtpt', xyz_tag(D50)),
        ('rXYZ', xyz_tag([m[i][0] for i in range(3)])),
        ('gXYZ', xyz_tag([m[i][1] for i in range(3)])),
        ('bXYZ', xyz_tag([m[i][2] for i in range(3)])),
        ('vcgt', vcgt_tag(gains)),
        ('rTRC', curv_tag(GAMMA)),
        ('gTRC', curv_tag(GAMMA)),
        ('bTRC', curv_tag(GAMMA)),
    ]
    offset = 128 + 4 + 12 * len(tags)
    table, body = b'', b''
    for sig, data in tags:
        table += sig.encode() + struct.pack('>II', offset + len(body), len(data))
        body += data + b'\0' * (-len(data) % 4)
    now = datetime.datetime.now(datetime.timezone.utc)
    header = struct.pack('>I4sI4s4s4s', offset + len(body), b'lcms', 0x02100000, b'mntr', b'RGB ', b'XYZ ')
    header += struct.pack('>6H', now.year, now.month, now.day, now.hour, now.minute, now.second)
    header += b'acsp' + b'*nix' + b'\0' * 12 + b'\0' * 8 + struct.pack('>I', 0)
    header += b''.join(s15(c) for c in D50) + b'lcms' + b'\0' * 44
    return header + struct.pack('>I', len(tags)) + table + body


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-r', type=float, default=DEFAULT_GAINS[0], help='red gain (default %(default)s)')
    p.add_argument('-g', type=float, default=DEFAULT_GAINS[1], help='green gain (default %(default)s)')
    p.add_argument('-b', type=float, default=DEFAULT_GAINS[2], help='blue gain (default %(default)s)')
    p.add_argument('-o', default='AUO3CA2_Dell_G16_final.icc', help='output file')
    a = p.parse_args()
    gains = (a.r, a.g, a.b)
    with open(a.o, 'wb') as f:
        f.write(build(gains, f'AUO3CA2 Dell G16 vcgt R{a.r} G{a.g} B{a.b}'))
    print(f'wrote {a.o} with gains R={a.r} G={a.g} B={a.b}')
    print(f'apply with: kscreen-doctor output.eDP-1.iccprofile.$(realpath {a.o}) output.eDP-1.colorProfileSource.ICC')


if __name__ == '__main__':
    main()
