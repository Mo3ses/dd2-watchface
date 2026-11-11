# Formato do `.hwt` / `watchface.bin` (lite wearable, HWHD)

Documento de campo. Tudo marcado **[verificado]** foi confirmado neste projeto
contra pacotes reais ou contra o codec aberto do JoyoFit; o resto está marcado
como **[inferido]**.

Fontes: `packages/hwt/README.md` do JoyoFit (AGPL-3.0), engenharia reversa do
schema v2 do Theme Studio, e as 81 imagens do `SpaceRed.hwt` + o seed HWHD06.
Nenhuma amostra deste projeto foi exportada pelo Theme Studio Pro.

## Pacote

`.hwt` é um zip. Entradas observadas, nesta ordem:

```
com.huawei.watchface      binário (flat) ou zip com watchface.bin + res/ + config.xml (nested)
description.xml
preview/                  cover.jpg, aod.jpg (~816x960), icon_small.jpg (~331x390)
```

`description.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<HwTheme>
  <title>ARISEN HUD</title><title-cn>ARISEN</title-cn>
  <author>...</author><designer>...</designer>
  <screen>HWHD06</screen><version>2.1.4</version>
  <font>Default</font><font-cn>默认</font-cn><briefinfo>{}</briefinfo>
</HwTheme>
```

## Códigos de tela

| código | resolução | aparelho |
|---|---|---|
| HWHD02 | 454×454 | GT 2 46 mm |
| HWHD06 | **456×280** | Watch Fit / Watch Fit Special Edition |
| HWHD07 | 368×194 | Band 9 |
| HWHD09 | 466×466 | Watch 3/4, GT 4/5/6 |
| HWHD11 | 480×336 | Watch Fit 2 |
| HWHD13 | 480×408 | Watch Fit 3/4/4 Pro/5 |

## `watchface.bin`

```
off  size
0    u16le version     1 ou 2
2    u16le layoutLen   bytes do layout (protobuf)
4    u32le tableLen    8 × número de imagens
8    u32le binLen      bytes do fim da tabela até o EOF
12   u32le reserved    0
16   layout[layoutLen]
     table[tableLen]   { u32le offset, u32le size } por imagem
     bin[binLen]       8 bytes de assinatura + imagens em sequência
```

Regras **[verificado]**:

- `16 + layoutLen + tableLen + binLen == tamanho do arquivo`.
- offsets da tabela contam do começo do bin; a primeira imagem começa em 8.
- imagens tileiam sem buraco nem sobreposição.
- assinatura observada: `55 55 55 55 01 00 00 01` (e `2e2e2e2e…` numa amostra).
- slot 0 é a thumbnail do seletor e não é referenciado pelo layout (1-based: `"001"` = índice 0).

## Blob de imagem

```
45 23 88 88   magic
u16le width, u16le height
pixels BGRA(4) com escape: 89 67 45 23 + BGRA + u32le count
```

**[verificado]** em 81/81 imagens de uma face real: decode + encode com
`min_run=4` reproduz os bytes originais. Pixel que caia na cor de escape tem
que ser escrito como run de 1.

## Layout v2 (protobuf)

Mensagens usadas:

```
Watchface 1 element*, 2 title_en, 3 title_cn
Element   1 label, 2 is_support_option, 4 res_preview, 5 layer*, 8 container*
Layer     1 index, 2 draw_type, 4 single_res, 5 selected_res, 6 combined_res
Container 1 index, 2 is_support_option, 5 rect, 6 layer*, 8 data_type
Combined  1 res_name*, 2 res_default, 3 res_position(Point), 4 res_align,
          5 value_type, 6 res_sign, 7 x_offset, 8 y_offset, 13 ambient_mode
Single    1 res_name, 2 res_position, 5 ambient_mode
Rect      1 x, 2 y, 3 width, 4 height      Point 1 x, 2 y
```

Enums:

```
ElementLabel 0 BACKGROUND 1 TIME 2 DATE 3 WIDGET 4 COMPLICATION
LayerDrawType 0 text 1 single 2 selected 3 combined 5 hand 6 line 7 arc 10 text2 13 arc_text
AlignType 0 LEFT 1 CENTER 2 RIGHT
AmbientMode 0 NORMAL_ONLY 1 AMBIENT_ONLY 2 AMBIENT_NORMAL
```

Regras de campo **[verificado]**:

- `Point.x/y` e `Rect.x/y` são uint32 na wire; negativo vai como complemento de 2.
- Container precisa de `2: is_support_option` (0). Sem ele o elemento WIDGET é
  descartado pelo firmware — foi o que deixou duas células em branco.
- `Combined` traz `2: ""`, `6: ""`, `7: 0`, `8: 0` mesmo vazios.
- elemento WIDGET no `myface.hwt` não tem `4: res_preview`.

## Tipos de valor

| id | dado | evidência |
|---|---|---|
| 0 | passos | verificado |
| 2 | batimento | verificado |
| 4 | temperatura | verificado |
| 8 | altitude | verificado |
| 9 | bateria (power) | verificado |
| 12 | hora | verificado |
| 13 | minuto | verificado |
| 17 | dia do mês | verificado |
| 51 | mês | verificado |
| 52 | dia da semana | verificado |
| 248 | condição do clima | verificado |
| 59–62 | hora/minuto dezena/unidade | inferido |
| 1, 3 | caloria (ambíguo) | **não resolvido** |

Container `data_type`: 10 passos, 11 batimento, 17 bateria, 21 clima (hospeda
temperatura), 22 altitude **[verificado em face real]**.

## Limites

`watchface.bin` ≤ 9,5 MB; `.hwt` ≤ 10 MB; imagem ≤ 750 KB comprimida;
Σ w·h·4 ≤ 4 MiB. Cor de fundo preta total ajuda a bateria em AMOLED.
