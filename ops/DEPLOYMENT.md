# Implantação Locaweb + Ubuntu

## 1. Bloqueio obrigatório: inventário do Ubuntu

Antes de `apt`, `pip`, criação de usuário, cópia de unit ou escolha de porta, execute:

```bash
sh ops/ubuntu-inventory.sh | tee musiclite-inventory.txt
```

Revise especialmente `ss -ltnp`, todos os services/timers, `nvidia-smi`, processos Python/CUDA, ambientes virtuais, modelos e os recursos do eBookLite. Não continue se houver dúvida sobre impacto. O script é somente leitura.

Não alterar/parar/reinstalar: Ollama 11434, ComfyUI 8188, `ebooklite-worker.service`, timer/watchdog, `/opt/ebooklite`, `/var/lib/ebooklite`, `/etc/ebooklite/worker.env`, ambientes/modelos/usuários existentes ou tabelas `ebook_ai_*`. Não instalar nada no Python do ComfyUI nem substituir CUDA, PyTorch ou driver.

Depois do inventário, verifique se já existe gerador compatível. Somente se não existir, documente a opção proposta, licença, disco, RAM, VRAM, versão CUDA/PyTorch isolada e porta livre, e obtenha aprovação antes da instalação.

## 2. Locaweb

1. Faça backup e publique os arquivos de forma aditiva.
   Use PHP 8.1 ou superior com `mysqli`, `curl`, `json`, `fileinfo` e `mbstring`.
2. Aplique `migrations/20260815_music_ai.sql` na base do eMusic Lite.
3. Configure as variáveis de `.env.example` no painel/ambiente PHP. Não publique arquivo `.env`.
4. Gere segredos independentes, por exemplo `openssl rand -hex 32`, um para `MUSIC_AUTH_SUBJECT_KEY` e outro para `MUSIC_AI_INGEST_SECRET`.
5. Defina `MUSIC_AI_PUBLIC_MEDIA_PATH` em diretório gravável. Se estiver sob o document root, bloqueie acesso direto e sirva exclusivamente por `api/music/media.php`.
6. Garanta `ffprobe` disponível para a segunda validação do áudio.
7. Confirme que `worker-audio-ingest.php` e `worker-cover-ingest.php` são acessíveis somente por HTTPS.
8. Libere MySQL remoto apenas para o IP de saída do Ubuntu, com usuário de privilégio mínimo sobre `music_ai_*` e leitura de `ebook_ai_jobs`/`ebook_ai_settings` somente para a guarda de recursos.
9. Faça o primeiro login, consulte o ID em `music_ai_users` e configure `MUSIC_AI_ADMIN_USER_IDS`.

## 3. Ubuntu, somente após aprovação do inventário

Os comandos abaixo não devem ser executados antes da etapa 1:

```bash
sudo useradd --system --home /var/lib/musiclite --shell /usr/sbin/nologin musiclite
sudo install -d -o musiclite -g musiclite -m 0750 /opt/musiclite /var/lib/musiclite /var/log/musiclite
sudo install -d -o root -g musiclite -m 0750 /etc/musiclite
sudo python3 -m venv /opt/musiclite/venv
```

Copie somente o código MusicLite para `/opt/musiclite`; nunca sobreponha `/opt/ebooklite`. Copie `ops/worker.env.example` para `/etc/musiclite/worker.env`, preencha sem reutilizar segredos e aplique modo `0640 root:musiclite`.

Escolha a porta do gerador apenas a partir da lista livre do inventário e configure `MUSIC_AI_GENERATOR_URL`. O Ollama e o ComfyUI continuam em 11434/8188 apenas como APIs existentes.

### Backend ACE-Step isolado aprovado para este host

O adaptador HTTP entregue em `ops/generator/` implementa o contrato de `MusicGenerationService`. Ele deve ser copiado para `/opt/musiclite/api/`, enquanto o repositório ACE-Step permanece em `/opt/musiclite/generator` e usa exclusivamente `/opt/musiclite/venv` e `/var/lib/musiclite/models`.

```bash
sudo install -d -o musiclite -g musiclite -m 0750 /opt/musiclite/api /var/lib/musiclite/generator-output
sudo install -o musiclite -g musiclite -m 0640 ops/generator/musiclite_generation_spec.py /opt/musiclite/api/
sudo install -o musiclite -g musiclite -m 0750 ops/generator/musiclite_generator_api.py /opt/musiclite/api/
sudo install -o musiclite -g musiclite -m 0640 ops/comfy/comfy-cover-workflow.json /opt/musiclite/config/comfy-cover-workflow.json
```

O serviço vincula apenas em `127.0.0.1`, exige Bearer token próprio de no mínimo 32 caracteres, aceita uma geração por vez e recusa iniciar geração pesada sem o mínimo configurado de VRAM livre. Não exponha a porta do gerador na rede.

Valide antes de habilitar:

```bash
sudo -u musiclite /usr/bin/php /opt/musiclite/workers/worker_preflight.php
sudo -u musiclite /usr/bin/php /opt/musiclite/tests/music_ai_tests.php
```

Instale apenas as units MusicLite e então habilite:

```bash
sudo install -m 0644 /opt/musiclite/ops/systemd/musiclite-generator.service /etc/systemd/system/
sudo install -m 0644 /opt/musiclite/ops/systemd/musiclite-worker.service /etc/systemd/system/
sudo install -m 0644 /opt/musiclite/ops/systemd/musiclite-worker-watchdog.service /etc/systemd/system/
sudo install -m 0644 /opt/musiclite/ops/systemd/musiclite-worker-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now musiclite-generator.service
sudo systemctl enable --now musiclite-worker.service
sudo systemctl enable --now musiclite-worker-watchdog.timer
systemctl status musiclite-generator.service --no-pager
systemctl status musiclite-worker.service --no-pager
journalctl -u musiclite-worker.service -f
```

Antes de habilitar, confirme no venv isolado que `fastapi` e `uvicorn` estão importáveis. Se estiverem ausentes, instale-os somente em `/opt/musiclite/venv`; nunca no Python do ComfyUI nem globalmente.

O horário `daily_agent_time` deve ser diferente do agente de livros. O preflight bloqueia horários iguais quando consegue ler `ebook_ai_settings`.

Quando as tabelas `music_ai_*` e `ebook_ai_*` estiverem em servidores MySQL diferentes, configure a conexão de guarda independente com `MUSIC_AI_EBOOK_DB_HOST`, `MUSIC_AI_EBOOK_DB_PORT`, `MUSIC_AI_EBOOK_DB_NAME`, `MUSIC_AI_EBOOK_DB_USER` e `MUSIC_AI_EBOOK_DB_PASSWORD`. Essa conta deve possuir somente `SELECT` em `ebook_ai_jobs` e `ebook_ai_settings`; nunca copie automaticamente a credencial de escrita do eBookLite.

## 4. Validação final

- Crie projeto por dois usuários e confirme isolamento de IDs.
- Provoque queda após cada checkpoint e execute worker `--once`; nada já concluído deve ser recriado.
- Reenvie um request UUID e confirme HTTP 409.
- Tente publicar sem áudio/capa e confirme bloqueio.
- Confirme catálogo somente com `COMPLETED + is_published=1`.
- Deixe um `ebook_ai_jobs` em `processing` em ambiente de teste e confirme que a música permanece pendente.
- Verifique que nenhuma unit, porta, diretório ou processo eBookLite mudou.
- Confirme que a música cadastrada chega a `COMPLETED`, permanece privada e possui os dez checkpoints. A publicação continua sendo uma ação exclusiva do proprietário.
