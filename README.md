# ARISEN HUD · dd2-watchface

Face para **HUAWEI WATCH FIT Special Edition (STA-B39)** — HarmonyOS 2.1,
AMOLED **280 × 456**, identidade do rice Dragon's Dogma 2.

O projeto tem três camadas independentes:

1. **Arte** (`gen_assets.py`): fundo HUD, brasa, rótulos, atlas de dígitos, AOD,
   thumbnail. Tudo desenhado em Pillow com a fonte local.
2. **Layout** (`tools/layout.py`): edita o protobuf do `watchface.bin` — posição
   e alinhamento da hora, e containers de widget (batimento, bateria, clima).
3. **Empacotamento** (`tools/hwformat.py`): escreve header, tabela e blobs de
   imagem no formato do firmware, com verificação antes de salvar.

Estado atual: **face instalada no relógio**, hora viva, fundo com a arte do
coração de brasa. Batimento e bateria estão no layout (v4) aguardando teste no
pulso. Temperatura e caloria são o próximo corte.

## estrutura

```
gen_assets.py             gerador de sprites (Pillow)
tools/hwformat.py         leitor/escritor do watchface.bin
tools/layout.py           editor do layout protobuf (schema v2)
tools/layout_info.py      resumo legível de elementos/layers/containers
tools/build_face.py       monta as variantes v0..v4 sobre o seed
tools/artbg.py            fundo a partir de fundo.jpg + rótulos
tools/inspect_hwt.py      inventário de slots de um .hwt
tools/pack_hwt.py         troca sprites por slotmap
tools/sim_preview.py      simula o render do relógio
tools/mockup.py           põe o render no corpo do relógio
tools/dumppb.py           despeja a árvore protobuf do layout
tools/selftest.py         codec ida-e-volta (pacotes sintéticos)
tools/reencode_check.py   confere re-encode contra amostra real
docs/FORMAT.md            formato do pacote, bin e layout
```

Pastas ignoradas pelo git: `build/`, `out/`, `base/`, `fonts/` — artefatos,
seeds de terceiros e a fonte licenciada ficam fora do repositório.

## fonte

`gen_assets.py` procura `--font`, `DD2_FONT`, `fonts/*Terminess*` e as fontes do
sistema, nessa ordem. Sem Terminess ele cai em Cascadia Mono e avisa.

```powershell
copy <caminho>\TerminessNerdFontMono-Bold.ttf .\fonts\
python gen_assets.py --strict
```

`--strict` falha se o fundo cair abaixo de 80% de preto puro (medição atual:
86,5%). A hora é auto-ajustada para caber em 236 px.

## seed

O `watchface.bin` carrega a config (elementos, layers, value types). Em vez de
reescrever o schema inteiro, o projeto usa um pacote mínimo **HWHD06** gerado
pelo JoyoFit Studio (`base/myface.hwt`) como esqueleto: ele doa os elementos e
o `description.xml`, e o builder troca pele e geometria.

## build

```powershell
python gen_assets.py --strict     # sprites + preview
python tools/artbg.py             # fundo a partir da arte + rótulos
python tools/build_face.py        # out/ARISEN_HUD_v0..v4.hwt
python tools/sim_preview.py out\ARISEN_HUD_v4.hwt --time 9:11 --values "hr=62,cal=412,temp=24,bat=87"
python tools/mockup.py out\ARISEN_HUD_v4_sim.png out\preview_v4.png
```

Variantes:

| versão | o que muda |
|---|---|
| v0 | dígitos do tamanho do seed (50×53) |
| v1 | dígitos grandes (51×111) |
| v2 | v1 + hora/minuto ancorados à direita (`9` e `09` no mesmo pixel) |
| v3 | v2 + containers de batimento e bateria |
| v4 | v3 + arte do `fundo.jpg` como fundo e rótulos assentes nela |

## instalar (iPhone → relógio)

1. Sideloadly no Windows + Apple ID grátis (7 dias por assinatura).
2. Sideload do `HuaSideload-1.1.ipa` (repo `Burak4Arslan/huawei-watch-sideload-ios`).
3. `Ajustes > Geral > VPN e Dispositivo > Desenvolvedor da Apple > Confiar` e
   `Ajustes > Privacidade e Segurança > Modo Desenvolvedor`.
4. No app: **Watch → Pair**, depois **Install → Watch faces → .hwt**.
5. Fechar o Huawei Health durante o pareamento — os dois brigam pelo BLE.

Firmware 2.x aceita face sem assinatura de servidor. O bloqueio por assinatura
RSA entrou no 6.0.0.328+.

## limites conhecidos

- **caloria**: o id não está resolvido (1 ou 3, ambos ambíguos na documentação).
- **temperatura** vem do clima sincronizado pelo celular; sem sync, `--`.
- A arte 1536×2752 é esticada ~9% no eixo vertical para 280×456; o frame é
  desenhado em 9:16 e o relógio é 0,614.
- Firmware 6.1+ exige assinatura da Huawei para face e para app — não se aplica
  ao 2.1, mas trava migração futura de relógio.
