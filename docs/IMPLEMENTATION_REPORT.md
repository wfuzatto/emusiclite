# Relatório de implementação

## Projeto encontrado

O eMusic Lite existente é uma aplicação PHP 8 procedural, sem framework ou Composer, com MySQLi, sessão baseada em CPF validado por serviço externo, páginas monolíticas (`dashboard.php`, `admin.php`) e player em JavaScript. O catálogo original usa `tracks`; os arquivos existentes e o estilo escuro/verde foram preservados.

## Entrega adicionada

- Migration versionada e idempotente `migrations/20260815_music_ai.sql`, com 12 tabelas exclusivamente `music_ai_*`.
- Identidade interna pseudonimizada e usuário `Agente Musical eMusic Lite`, código `AGENTE-MUSICAL`, tipo/status de sistema e sem CPF.
- Serviços de projeto, moderação, plano no Ollama, fila, checkpoints, áudio, capa, recursos de GPU, ingestão e agente diário em `services/`.
- Interface `MusicGenerationService`, backend HTTP configurável e backend inicial `unconfigured`.
- Worker persistente, agente diário, heartbeat auxiliar durante tarefas longas, preflight, recuperação após parada e watchdog em `workers/`.
- Endpoints autenticados em `api/music/`; ingestão separada em `worker-audio-ingest.php` e `worker-cover-ingest.php`.
- Telas `criar-musica.php`, `minhas-musicas.php` e `ai-agent.php`, integradas ao visual existente.
- Mídia privada servida somente ao dono; mídia concluída e publicada pode ser reproduzida pelo catálogo, com suporte a Range/HEAD e acesso direto ao diretório negado por `.htaccess`.
- Units exclusivas `musiclite-worker*`, sem dependência de controle sobre units do eBookLite.
- Exemplos de ambiente sem segredos em `.env.example` e `ops/worker.env.example`.
- Inventário somente leitura e implantação documentados em `ops/ubuntu-inventory.sh` e `ops/DEPLOYMENT.md`.
- Smoke test reproduzível do backend em `ops/musiclite_generate_test.py`.

## Migration

Aplicar na base do eMusic Lite:

```bash
mysql -u USUARIO -p NOME_DA_BASE < migrations/20260815_music_ai.sql
```

Ela cria: `music_ai_migrations`, `music_ai_users`, `music_ai_tracks`, `music_ai_track_plans`, `music_ai_lyrics`, `music_ai_jobs`, `music_ai_media`, `music_ai_agent_runs`, `music_ai_workers`, `music_ai_logs`, `music_ai_settings` e `music_ai_ingest_requests`.

Nenhuma tabela `ebook_ai_*` é alterada.

## Verificações executadas

- Lint PHP 8.2 em todos os arquivos: aprovado.
- Sintaxe JavaScript dos três novos scripts: aprovada.
- Sintaxe POSIX shell do inventário: aprovada.
- Migration executada e reexecutada no MySQL local: aprovada/idempotente.
- `tests/music_ai_tests.php`: 29 testes aprovados, 0 falhas.
- Sintaxe do script Python de smoke test: aprovada.
- Geração real ACE-Step: aprovada; áudio de teste validado com `ffprobe` e copiado para `assets/audio/Amanhecer-1604.mp3`.
- Contrato do adaptador ACE-Step: 4 testes Python aprovados, 0 falhas.
- Workflow de capa ComfyUI: JSON válido e composto somente por nodes padrão já disponíveis.
- Ingestão HTTPS/HMAC: assinatura, CA, multipart e validação de propriedade exercitados; request de projeto inexistente foi rejeitado sem mutação.
- FFmpeg/ffprobe 9.0.1 instalado no ambiente XAMPP local; o MP3 de smoke test passou também por `AudioValidationService` (MP3, 30 s, 48 kHz, estéreo, 721.197 bytes).

Os testes incluem propriedade, edição indevida, publicação incompleta, idempotência da fila, antirreplay, chave diária, recuperação de worker parado e queda simulada após cada um dos dez checkpoints.

## Inventário e validação no Ubuntu

O inventário obrigatório foi executado antes de qualquer instalação. O host possui Ubuntu 22.04, GTX 1060 6 GB, Ollama ativo em 11434 e ComfyUI ativo em 8188. Os serviços, processos, ambientes, modelos e portas existentes foram preservados. Não foram encontradas units ou tabelas `ebook_ai_*` nesse host; ainda assim, as guardas permanecem implementadas. A porta 8091 estava livre e foi reservada para o futuro backend MusicLite.

Com aprovação explícita, foi instalado de forma isolada:

- usuário de sistema `musiclite`;
- código ACE-Step 1.5 em `/opt/musiclite/generator`, commit `6d467e4b5081ccb0abf1ec1bf4fdf9051a2d34b0`;
- Python 3.11 e venv exclusivo em `/opt/musiclite/venv`;
- modelos em `/var/lib/musiclite/models` e saída em `/var/lib/musiclite/output`;
- PyTorch 2.10.0+cu126 somente nesse venv, necessário para a arquitetura Pascal `sm_61` da GTX 1060;
- ACE-Step 2B turbo com INT8, offload completo, lote pesado máximo 1 e LM desativado.

Nenhum pacote global, driver, CUDA, ambiente do ComfyUI, serviço existente ou modelo de outra aplicação foi alterado. O servidor HTTP temporário usado para copiar o MP3 foi encerrado e a porta 8091 voltou a ficar livre.

### Música de smoke test

- Título: `Amanhecer 1604`.
- Instrumental, 104 BPM, Ré maior, 30 segundos, seed 1604.
- WAV original: PCM 16-bit, 48 kHz, estéreo, 30,000 s, 5.760.078 bytes.
- Volume: média -15,9 dB, pico -1,0 dB.
- SHA-256 WAV: `27933df7559524434402c46e53b8bf2155f0edaf5f18b01da3c430d69be5db94`.
- MP3: 48 kHz, estéreo, 192 kbps, 30,024 s, 721.197 bytes.
- SHA-256 MP3: `d0ce8a8cbc36e2dc36e6794bdf1e3092157b630b7ad72778d6c55c926d6ab2bf`.

Após a execução, a GPU retornou a 0% de uso e 5.866 MiB livres; Ollama e ComfyUI permaneceram ativos e a fila do ComfyUI permaneceu vazia.

## Itens ainda dependentes de configuração externa

- domínio HTTPS e publicação dos arquivos PHP na Locaweb;
- credenciais MySQL remotas de privilégio mínimo;
- segredo musical novo para HMAC e demais variáveis reais de ambiente;
- ID interno dos administradores após o primeiro login;
- nome de modelo Ollama já autorizado e workflow de capa compatível com os modelos existentes;
- implantação da aplicação/worker PHP no Ubuntu e habilitação das units MusicLite;
- ativação persistente do servidor ACE-Step na porta reservada após configurar `/etc/musiclite/worker.env`.

O adaptador persistente, a unit `musiclite-generator.service` e o workflow de capa estão versionados no projeto. Após o restabelecimento da autenticação SSH, o inventário foi repetido antes de continuar a implantação.

## Estado da implantação após restabelecimento do SSH

- Inventário repetido antes das alterações; eBookLite, watchdog, Ollama, ComfyUI, ambientes, modelos e processos existentes permaneceram ativos.
- Código PHP, adaptador ACE-Step, workflow e quatro units MusicLite instalados de forma aditiva nos diretórios exclusivos.
- `musiclite-generator.service` habilitado e saudável, vinculando apenas em loopback e sem carregar o modelo ou reservar VRAM durante ociosidade.
- Worker e watchdog MusicLite mantidos desabilitados enquanto existe trabalho `ebook_ai_jobs` em processamento.
- Conexão ao banco musical e ingestão HTTPS/HMAC de saída validadas sem alterar a música cadastrada.
- O banco do eBookLite está em servidor diferente. A conta editorial atual não pode criar o usuário `musiclite_guard`; é necessária uma conta externa somente leitura ou autorização explícita para uma alternativa. O preflight bloqueia o worker até isso ser resolvido.

## Primeira música processada pela plataforma

- Projeto `7`, título planejado `EletroVibes`, concluído e publicado pelo proprietário.
- Planejamento, letra instrumental, prompt, áudio, validação, ingestão, capa e ingestão da capa persistidos como checkpoints.
- Áudio WAV: 60 segundos, 48 kHz, estéreo, checksum confirmado e nova validação com `ffprobe` aprovada.
- Capa PNG: 768 × 768, checksum confirmado.
- A primeira ingestão revelou ausência de escrita do Apache no armazenamento local. Foi aplicada ACL somente ao usuário do servidor web em `storage/music-ai`; a retomada reutilizou o áudio validado e concluiu sem duplicá-lo.
- O robô diário foi ajustado para não acionar a própria regra de moderação com instrução negativa e para que uma falha editorial isolada nunca encerre o daemon da fila.
- Gerador, worker e watchdog MusicLite ficaram ativos após preflight; Ollama, ComfyUI e todos os serviços do eBookLite permaneceram ativos.
- A reprodução HTTP foi validada pela rota exata usada pela interface: áudio PCM WAV de 60 segundos decodificado via URL pelo `ffprobe`, resposta parcial `206` com `audio/wav`, capa `200 image/png` e Range de sufixo aprovado.
- Foi corrigida a validação do diretório de mídia para usar identidade de filesystem, evitando falso 404 no macOS quando a URL usa capitalização diferente (`eMusiclite`/`eMusicLite`).

Até essas credenciais e URLs serem configuradas, `MUSIC_AI_GENERATOR_BACKEND=unconfigured` faz o preflight do worker PHP bloquear a inicialização de forma segura. O gerador isolado já foi validado por execução direta, mas não foi deixado como daemon público.
