[English](README.md) | **Tiếng Việt**

# Máy rửa chén Midea / Comfee (E1) — Tiện ích cho Home Assistant

Tiện ích nhỏ giúp điều khiển máy rửa chén Midea/Comfee (device type `0xE1`) tại chỗ (local) qua [Home Assistant](https://www.home-assistant.io/) với integration [`midea_ac_lan`](https://github.com/wuwentao/midea_ac_lan).

Gồm:
- `get_e1_lua.py` — đăng nhập tài khoản Midea/MSmartHome và tải file giao thức (Lua) của thiết bị từ cloud, để dùng với các integration điều khiển local.
- **Bảng lệnh** sẵn dùng cho máy rửa chén E1 qua `midea_ac_lan.send_command`.

## Yêu cầu

```bash
pip install requests pycryptodome
```

## Cách dùng

```bash
python get_e1_lua.py            # nhập account + password khi được hỏi
```

Script đăng nhập cloud MSmartHome **global** (`mp-prod.appsmb.com`), liệt kê thiết bị, và lưu file Lua của từng thiết bị vào `lua_out/`. Tài khoản/mật khẩu nhập tương tác lúc chạy, không lưu ra file.

> Tài khoản overseas/global phải dùng server global. Server China (`smartmidea.net`) sẽ từ chối tài khoản global với lỗi `mobile ... illegal`.

## Bảng lệnh máy rửa chén E1

Gửi bằng service `midea_ac_lan.send_command` (`cmd_type: 2`). `cmd_body` bắt đầu bằng byte body-type.

```yaml
action: midea_ac_lan.send_command
data:
  device_id: <id thiết bị của bạn>
  cmd_type: 2
  cmd_body: "0803040000"   # ví dụ: start ECO
```

### Nguồn / start / mode — `08 | work_status | mode | 00 00`
- Power ON: `0801000000` · Power OFF: `0800000000`
- Start chương trình: `0803` + `mode` + `0000`

Mode: auto`01` intensive`02` normal`03` eco`04` glass`05` 90min`06` rapid`07` soak`08`
1hour`09` 3in1`0A` auto_heavy`0B` party`0C` quiet`0D` auto_daily`0E` hygiene`0F` self_clean`10` auto_glass`11` baby_care`12` fruit`13`.

### Operator / khoá — `83 | value`
- Start / resume: `8301` · Pause: `8302`
- Khoá trẻ em ON / OFF: `8303` / `8304`

### Công tắc chức năng — `81 00 00 00 …` (byte không đổi = `FF`)
- dry → byte9 (0=off, 1=on, 2=đang sấy), số phút sấy → byte10
- uv → byte7 · water → byte8 · dry-step → byte6 · storage → byte4

> Lưu ý: trên model này "Dry" là một giai đoạn của chu trình rửa, không phải chương trình độc lập (không có mode "chỉ sấy" riêng).

## Ghi công

- [`wuwentao/midea_ac_lan`](https://github.com/wuwentao/midea_ac_lan) — điều khiển local trên Home Assistant.
- [`mill1000/midea-msmart`](https://github.com/mill1000/midea-msmart) — client cloud MSmartHome.
- [`Cyborg2017/midea_device_fetcher`](https://github.com/Cyborg2017/midea_device_fetcher) — công cụ tải Lua thiết bị.

Dùng cho mục đích cá nhân/tương tác với thiết bị bạn sở hữu. Không liên kết với Midea/Comfee.
