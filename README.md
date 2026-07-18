**English** | [Tiếng Việt](README.vi.md)

# Midea / Comfee Dishwasher (E1) — Home Assistant Helper

A small helper for controlling a Midea/Comfee dishwasher (device type `0xE1`) locally through [Home Assistant](https://www.home-assistant.io/) with the [`midea_ac_lan`](https://github.com/wuwentao/midea_ac_lan) integration.

It contains:
- `get_e1_lua.py` — logs into your Midea/MSmartHome account and downloads your device's protocol (Lua) files from the cloud, so you can use them with local-control integrations.
- A ready-to-use **command reference** for the E1 dishwasher via `midea_ac_lan.send_command`.

## Requirements

```bash
pip install requests pycryptodome
```

## Usage

```bash
python get_e1_lua.py            # enter your account + password when prompted
```

It logs into the **global** MSmartHome cloud (`mp-prod.appsmb.com`), lists your appliances, and saves each device's Lua file under `lua_out/`. Credentials are entered interactively at runtime and never stored.

> An overseas/global account must use the global server. The China server (`smartmidea.net`) will reject a global account with `mobile ... illegal`.

## E1 dishwasher command reference

Send with the `midea_ac_lan.send_command` service (`cmd_type: 2`). `cmd_body` starts with the body-type byte.

```yaml
action: midea_ac_lan.send_command
data:
  device_id: <your device id>
  cmd_type: 2
  cmd_body: "0803040000"   # example: start ECO
```

### Power / start / mode — `08 | work_status | mode | 00 00`
- Power ON: `0801000000` · Power OFF: `0800000000`
- Start a program: `0803` + `mode` + `0000`

Modes: auto`01` intensive`02` normal`03` eco`04` glass`05` 90min`06` rapid`07` soak`08`
1hour`09` 3in1`0A` auto_heavy`0B` party`0C` quiet`0D` auto_daily`0E` hygiene`0F` self_clean`10` auto_glass`11` baby_care`12` fruit`13`.

### Operator / lock — `83 | value`
- Start / resume: `8301` · Pause: `8302`
- Child lock ON / OFF: `8303` / `8304`

### Function switches — `81 00 00 00 …` (unchanged byte = `FF`)
- dry → byte9 (0=off, 1=on, 2=drying), dry minutes → byte10
- uv → byte7 · water → byte8 · dry-step → byte6 · storage → byte4

> Note: on this model "Dry" is a phase of a wash cycle, not a standalone program (there is no dry-only mode value).

## Credits

- [`wuwentao/midea_ac_lan`](https://github.com/wuwentao/midea_ac_lan) — Home Assistant local control.
- [`mill1000/midea-msmart`](https://github.com/mill1000/midea-msmart) — MSmartHome cloud client.
- [`Cyborg2017/midea_device_fetcher`](https://github.com/Cyborg2017/midea_device_fetcher) — device Lua fetcher.

For personal/interoperability use with hardware you own. Not affiliated with Midea/Comfee.
