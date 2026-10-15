# Dell G16 display tint fix

An ICC profile (and the script that generates it) that makes the built-in screen of the **Dell G16** look more neutral. **Whites and light colors become less yellowish and a little less green.**

The panel in the tested laptop is an AUO unit (EDID `AUO3CA2`, 2560x1600 @ 240 Hz) whose whites looked warm and slightly yellow-green next to a reference screen. The profile keeps the panel's own primaries and gamma and trims red and green slightly through a `vcgt` tag, which shifts the white point toward neutral.

> **This is an eyeball correction, not a measured calibration.** It was tuned by comparing against a MacBook screen, without a colorimeter. It makes whites look more neutral on the tested unit. Panels differ unit to unit, so your result may vary. For accurate colors, measure with a colorimeter (see [Proper calibration](#proper-calibration)).

## Quick start (KDE Plasma 6, Wayland)

1. Download `AUO3CA2_Dell_G16_final.icc` from this repo.
2. Put it somewhere stable:
   ```
   mkdir -p ~/.local/share/color/icc
   cp AUO3CA2_Dell_G16_final.icc ~/.local/share/color/icc/
   ```
3. Find your display name with `kscreen-doctor -o` (usually `eDP-1`) and apply the profile. Do not put quotes around the path:
   ```
   kscreen-doctor output.eDP-1.iccprofile.$HOME/.local/share/color/icc/AUO3CA2_Dell_G16_final.icc output.eDP-1.colorProfileSource.ICC
   ```
   You can also pick the file under System Settings, Color & Themes, Color Management.
4. Check it is active:
   ```
   kscreen-doctor -o | grep -iE "ICC profile|profile source"
   ```
   The source must say `ICC`. Setting a path while the source is still `EDID` does nothing.

To go back to the default colors:
```
kscreen-doctor output.eDP-1.colorProfileSource.EDID
```

## Check that it fits your laptop

The profile uses the primaries of the AUO panel. Check yours first:

```
edid-decode /sys/class/drm/card*-eDP-*/edid | grep -E "Manufacturer|Model"
```

If it says `AUO` with model `15522`, it is the same panel as the tested one. Other panels (BOE, LG, or other AUO models) have different primaries and white points, so use the script below with their EDID values instead.

## Generate your own profile

`make_profile.py` needs only Python 3 and nothing else.

```
./make_profile.py                      # final values, writes ./AUO3CA2_Dell_G16_final.icc
./make_profile.py -r 0.95 -g 0.94      # custom gains
./make_profile.py -r 0.95 -o ~/.local/share/color/icc/test.icc
```

The gains are multipliers for the red, green and blue channels (1.0 means unchanged):

- Lower **R** for less red, lower **G** for less green, lower both for less yellow overall.
- Change a little at a time (0.01 steps) and compare on screen.
- The script prints the `kscreen-doctor` command to apply the result.

Included presets, tested by eye (R / G / B):

| Variant | R | G | B | Notes |
|---|---|---|---|---|
| mild | 0.96 | 0.98 | 1.0 | slight, a little weak |
| between | 0.94 | 0.97 | 1.0 | good |
| medium | 0.92 | 0.96 | 1.0 | a bit too much |
| warmer_a | 0.95 | 0.95 | 1.0 | better, less green |
| warmer_b | 0.96 | 0.935 | 1.0 | too much red |
| **final** (default) | 0.955 | 0.9425 | 1.0 | best match to the reference screen |

To adapt the script to a different panel, edit `RED`, `GREEN`, `BLUE`, `WHITE` and `GAMMA` at the top with the values from your EDID (`edid-decode`).

## How it works

A hand-built ICC v2 matrix/TRC display profile: the panel's EDID primaries and white point, Bradford-adapted to D50, with gamma 2.2 curves, plus a `vcgt` table (3 channels, 256 entries, 16-bit, value = `i/255 * gain * 65535`).

What did not work, and why the tint lives in `vcgt`:

- Shifting the white point in the profile colorants or `wtpt` has **no visible effect**. KWin maps the profile white back to its own white.
- Night Light cannot cool the screen. Its day temperature is clamped at 6500K.
- The **`vcgt` tag works**. KWin 6.7 reads and applies it.

Tested on KDE Plasma 6.7.5, Wayland, CachyOS. Other desktops may handle `vcgt` differently.

## Proper calibration

If you have a colorimeter (i1Display, Spyder, and similar), DisplayCAL with ArgyllCMS can measure the screen and build an accurate profile. Install them with `sudo pacman -S displaycal` on Arch-based systems. On Wayland, load the resulting profile through System Settings, Color Management.

## License

MIT, see [LICENSE](LICENSE).
