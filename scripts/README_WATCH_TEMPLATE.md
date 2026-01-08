# 🎨 Watch Template - Desenvolvimento de Relatórios PDF

Script para desenvolvimento de templates HTML com **hot reload automático**.

## 🚀 Uso Básico

### Com contexto customizado (JSON)
```bash
python scripts/watch_template.py cloning_suspects_no_data_new tmp/cloning_no_data_context_example.json
```

## 📦 Estrutura do JSON de Contexto

O arquivo JSON deve conter todas as variáveis que o template espera.

### Exemplo: `tmp/cloning_context_example.json`

```json
{
  "styles_base_path": "/app/templates/styles_base.css",
  "logo_prefeitura_path": "/app/assets/logo_prefeitura.png",
  "logo_civitas_path": "/app/assets/logo_civitas.png",
  "icon_radar_path": "/app/assets/radar.png",
  "icon_warning_path": "/app/assets/warning.png",
  "icon_calendar_path": "/app/assets/calendar.png",
  "report_id": "20250101.101010000",
  "report_title": "Relatório de Suspeitas de Clonagem",
  "plate": "ABC1D23",
  "date_start": "01/06/2024",
  "date_end": "01/09/2024",
  "suspects": [
    {
      "plate": "ABC1D23",
      "detections_count": 45,
      "risk_level": "Alto"
    }
  ],
  "total_suspects": 2,
  "images_path": "/tmp/images/"
}
```

## ✨ Funcionalidades

### Auto-Reload
O navegador recarrega **automaticamente** quando você salva mudanças em:
- ✅ Template HTML (`app/templates/pdf/{template}.html`)
- ✅ CSS global (`app/templates/styles_base.css`)
- ✅ Arquivo JSON de contexto (se fornecido)

### Hot Reload em Tempo Real
- ⏱️ Verificação a cada 500ms
- 🔄 Reload automático sem F5
- 📝 Logs no console do navegador

## 📝 Workflow de Desenvolvimento

1. **Crie um JSON com dados de teste:**
   ```bash
   # Crie tmp/meu_contexto.json com os dados do seu relatório
   ```

2. **Rode o servidor:**
   ```bash
   python scripts/watch_template.py meu_template tmp/meu_contexto.json
   ```

3. **Desenvolva:**
   - Edite o template HTML
   - Edite o CSS
   - Edite o JSON de contexto
   - **Salve (Ctrl+S)** → navegador recarrega automaticamente! 🎉

4. **Iteração rápida:**
   - Ajuste cores no CSS → Salva → Vê resultado instantâneamente
   - Adiciona campo no template → Salva → Vê resultado instantâneamente
   - Muda dados no JSON → Salva → Vê resultado instantâneamente


## 📂 Estrutura de Arquivos

```
civitas-api/
├── scripts/
│   └── watch_template.py          ← Script principal
├── app/
│   ├── templates/
│   │   ├── styles_base.css        ← CSS global (monitorado)
│   │   └── pdf/
│   │       └── meu_template.html  ← Seu template (monitorado)
│   └── assets/
│       ├── logo_prefeitura.png
│       └── logo_civitas.png
└── tmp/
    └── meu_contexto.json          ← Dados de teste (monitorado)
```

## 🎯 Dicas

1. **Use dados reais no JSON** para simular o relatório final
2. **Mantenha o servidor rodando** durante todo o desenvolvimento
3. **Abra o DevTools** para ver erros de renderização
4. **F12 → Console** mostra logs úteis do auto-reload

## 🛠️ Troubleshooting

### CSS não carrega
Verifique se o caminho está correto no console:
```
🔍 Tentando servir: /app/templates/styles_base.css
✅ Arquivo encontrado: /home/.../app/templates/styles_base.css
```

### Imagens não aparecem
As imagens são servidas de `/app/assets/`. Verifique os logs.

### Auto-reload não funciona
Verifique o console do navegador (F12). Deve mostrar:
```
🔍 Monitorando mudanças no template...
```

Se não aparecer, recarregue a página manualmente (F5) uma vez.

## 💡 Exemplos de Uso

```bash
# Template simples sem dados
python scripts/watch_template.py template_base

# Template de clonagem com dados fake
python scripts/watch_template.py cloning_suspects tmp/cloning_context_example.json

# Template de placas correlacionadas com dados reais
python scripts/watch_template.py multiple_correlated_plates tmp/real_data.json
```