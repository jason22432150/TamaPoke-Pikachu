# TamaPoke 皮卡丘版

> **StackChan K151 開發分支：僅支援本機 USB 燒錄，不提供網頁刷機。** 目前 Alpha 尚未核准燒錄，請參閱 [macOS 本機安裝與前置檢查](boards/stackchan/ALPHA_INSTALL.md)。下方原始微雪 Waveshare 1.75 的網站及韌體僅適用於該板型，切勿用於 StackChan。

**拿一塊微雪開發板，用 USB 和瀏覽器就能刷入，接著開始照顧皮卡丘。**

## 新手從這裡開始

### [開啟網頁刷機與完整介面圖解](https://maxxtang.github.io/TamaPoke-Pikachu/)

不需要 Arduino IDE、Python 或程式經驗。用電腦版 Chrome／Edge，依序完成：

1. 接上 USB、核對完整板型。
2. 在網頁按「刷入遊戲」，等完成後關閉刷機視窗。
3. 按「連接並啟用皮卡丘」，自動設定角色、存檔與當地時間。
4. 看 [第一次安裝教學](docs/GETTING_STARTED.md) 與 [完整玩法圖解](docs/PLAYING.md)，開始餵食、陪玩、洗澡和休息。

**全新安裝會清除板上原有程式與存檔。沒有電池時請保持 USB 供電。**

網頁可選「先玩皮卡丘」或「完整 151 隻素材」。完整模式多一個 microSD 載入步驟：一般／異色動畫與圖鑑縮圖共 303 個檔案，約 42 MB。請準備已備份、可清空的 FAT32 卡片，至少約 64 MB 可用空間。**已有本版遊戲時可直接載入素材，不用重刷或清除存檔。** 詳見 [完整素材與記憶卡教學](docs/FULL_SPRITES.md)。

![網頁刷機與教學首頁](docs/images/web-home.jpg)

## 目前使用的開發板

**微雪 Waveshare ESP32-S3-Touch-AMOLED-1.75 原版開發板**：

| 項目 | 規格 |
| --- | --- |
| 晶片 | ESP32-S3 |
| 螢幕 | 1.75 吋、466 × 466 圓形 AMOLED，CO5300 |
| 觸控 | CST9217 |
| Flash / PSRAM | 16 MB / 8 MB OPI PSRAM |
| 本次韌體 | `1.19-pika` |

**1.75C 是不同板型，不適用本頁韌體。** 其他僅標示 ESP32-S3 的開發板也不代表相容。見 [微雪官方板卡資料](https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.75)。

## 遊戲畫面與玩法

以下為 **同版原始繪圖程式產生的介面示例，不是硬體實拍**；數值與狀態為示例。網頁提供 22 張可點開的介面與操作說明，包含主畫面、餵食、睡眠、洗澡、小遊戲、訓練、角色卡四頁、圖鑑、設定、命名、初始選角、蛋與成長／告別確認。

| 日常照顧 | 角色資料 |
| --- | --- |
| ![主畫面示例](web/assets/screens/home.png) | ![角色資料示例](web/assets/screens/profile.png) |
| ![餵食選單示例](web/assets/screens/feeding.png) | ![設定介面示例](web/assets/screens/settings.png) |

- **主畫面四按鈕**：食物、精靈球小遊戲、燈泡睡眠、洗澡。
- **需求條**：FOOD 飽足、JOY 心情、ENE 精力、HYG 清潔，越高越好。
- **向上滑**：角色卡，左右滑切換資料、能力、勳章與進度。
- **左右滑**：圖鑑；**向下滑**：時間、音量、亮度與語言。
- **輕點角色**：摸摸；**長按三秒**：放生確認。短按 PWR 只切換螢幕，不等於睡眠。

裝置預設英文，共有英、西、法、德、義、葡、日、韓八種語言，**沒有中文選項**；網站與教學用繁體中文逐項解說。

本版內建 #25 皮卡丘、#26 雷丘的一般／異色動畫，**玩皮卡丘不需要 microSD**。#1–9 另有簡單備用圖。完整 151 隻動畫及圖鑑縮圖放在 microSD，可透過網頁的完整素材模式載入；遊戲仍一次養一隻，圖鑑需逐步登錄。

## 版本與下載

[固定韌體 v1.19-pika](https://github.com/MAXXTANG/TamaPoke-Pikachu/releases/tag/v1.19-pika) 包含實機驗證的應用程式、全新安裝映像、原始碼 ZIP 與 SHA-256。

| 檔案 | 位址 | 用途 |
| --- | --- | --- |
| `firmware/tamapoke-1.19-pika-app.bin` | `0x10000` | 已有相同分割表時更新，這是當次實際刷入與校驗的應用程式 |
| `firmware/tamapoke-1.19-pika-factory.bin` | `0x0` | 全新安裝映像；網頁使用的就是這個固定檔案 |

網頁刷機包與保存版本逐位元相同。應用程式 SHA-256：

```text
d5da1d790d8794f92d8db0ff8cbbcffaaeb5ca0e3b7642451944a94e2133edbe
```

## 驗證與圖片來源

- 保存的應用程式已在相容板完成寫入校驗、啟動、無 microSD 皮卡丘載入與重開機存檔檢查。
- 原有 162 項主機遊戲測試與 sanitizer 檢查通過。
- 網頁另檢查 Web Serial 狀態辨識、取消、逾時、錯誤復原與當地時間換算，以及檔案／圖片完整性。
- 完整素材新增 13 項自動測試，涵蓋卡片與空間檢查、303 檔傳輸、ACK 逾時、停止及最終檔案核對；這些使用模擬序列埠。完整 microSD 寫入仍待插卡實測，不沿用無卡刷機的成功結果。
- 2026-11-23 已用 macOS Chrome 與原版微雪 1.75 板，完成公開網頁全新刷機、啟用 Lv.1 皮卡丘及硬體重開機存檔驗證；無 microSD，內建動畫載入成功。板上 bootloader、分割表與 app 雜湊均符合保存映像。使用者另確認皮卡丘畫面與觸控都正常。見 [實機測試與操作截圖](docs/HARDWARE_TEST.md)。
- 遊戲圖由 `tools/render_ui.py` 擷取實際繪圖程式、配合主機 RGB565 繪圖轉接器產生。示例值不是個人存檔，圖片來源見 `web/assets/screens/provenance.json`。
- `docs/images/` 為實際網頁介面截圖。

## 進階更新與重建

想保留已有存檔、從指令列刷回、重建原始碼或查看加密歷史封存，請看 [進階更新、重建與歷史封存](docs/ADVANCED.md)。

`web/` 是可直接部署的靜態網站，ESP Web Tools 10.4.0 隨站保存；`.github/workflows/pages.yml` 部署至 GitHub Pages。此網頁不自動載入全部 microSD 素材。

本機檢查：

```bash
node --test test/web-serial.test.mjs
python3 tools/check_web.py
make -C TamaPoke/test run asan
# 重新產生遊戲介面圖需要 Pillow 與 C++17 編譯器
python3 tools/render_ui.py
```

## 來源與授權

基於 [socquique/TamaPoke](https://github.com/socquique/TamaPoke) 的 [`00136942`](https://github.com/socquique/TamaPoke/commit/00136942f42c651ceb75fbfef8499a2df945cde7)。保留原作者署名與授權。

程式沿用 [MIT](LICENSE)，圖像依 PMD SpriteCollab 署名與非商業條件使用。Pokémon © Nintendo / Game Freak / The Pokémon Company。個人、非商業粉絲專案；詳見 [第三方標示](THIRD_PARTY_NOTICES.md) 與 [上游署名](docs/UPSTREAM_CREDITS.md)。
